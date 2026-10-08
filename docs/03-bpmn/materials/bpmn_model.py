"""Single source for the editable BPMN and its full/phase illustrations.

Orthogonal routing uses obstacle-aware grid search; illustrations are rendered
from the same nodes and flows, not arbitrary screenshot crops.
"""
from pathlib import Path
from xml.etree import ElementTree as ET
from html import escape
from collections import defaultdict
import heapq
import json
import textwrap

HERE = Path(__file__).resolve().parent
B = 'http://www.omg.org/spec/BPMN/20100524/MODEL'
D = 'http://www.omg.org/spec/BPMN/20100524/DI'
C = 'http://www.omg.org/spec/DD/20100524/DC'
I = 'http://www.omg.org/spec/DD/20100524/DI'
for prefix, uri in [('', B), ('bpmndi', D), ('dc', C), ('di', I)]:
    ET.register_namespace(prefix, uri)
LANES = ['Клиент', 'Менеджер', 'Логист', 'Диспетчер', 'Водитель', 'Бухгалтерия']
TITLES = ['Приём и уточнение заявки', 'Проверка возможности и расчёт',
          'Согласование условий', 'Назначение ресурсов и погрузка',
          'Перевозка и обработка отклонений', 'Претензии, документы и закрытие']
MAIN_ROUTE = ['Start_Request', 'Task_Request', 'Task_Register', 'Gateway_Complete',
              'Task_Check', 'Gateway_Feasible', 'Task_Calculate', 'Task_Offer',
              'Task_Approve', 'Gateway_Approved', 'Task_Assign', 'Gateway_Assigned',
              'Task_Route', 'Task_Arrival', 'Task_Load', 'Task_Monitor',
              'Gateway_Incident', 'Task_Deliver', 'Task_Proof', 'Gateway_Claim',
              'Task_Documents', 'Task_Invoice', 'Task_Payment', 'Task_Close', 'End_Closed']
NODES = {}
FLOWS = []
def node(id, name, lane, phase, col, track=0, kind='task', support=''):
    NODES[id] = dict(name=name, lane=lane, phase=phase, col=col, track=track, kind=kind, support=support)
def flow(a, b, label='', loop=False):
    FLOWS.append(dict(id=f'Flow_{len(FLOWS)+1:02}', a=a, b=b, label=label, loop=loop))

node('Start_Request', 'Потребность в перевозке', 0, 0, 0, kind='startEvent')
node('Task_Request', 'Передать заявку', 0, 0, 1, support='Бот собирает обязательные поля и показывает сводку')
node('Task_Register', 'Зарегистрировать и проверить заявку', 1, 0, 2, support='Карточка заказа, проверка полей, история уточнений')
node('Gateway_Complete', 'Данные полные?', 1, 0, 3, kind='exclusiveGateway')
node('Task_Ask', 'Запросить недостающие данные', 1, 0, 4, 1, support='Запрос только отсутствующих или некорректных полей')
node('Task_Clarify', 'Дополнить заявку', 0, 0, 4, 1)
node('Task_Check', 'Проверить возможность перевозки', 2, 1, 0, support='Карточка груза, ограничения маршрута и временного окна')
node('Gateway_Feasible', 'Перевозка возможна?', 2, 1, 1, kind='exclusiveGateway')
node('Task_Calculate', 'Рассчитать маршрут, срок и стоимость', 2, 1, 2, support='Версия расчёта и предложение; решение утверждает логист')
node('Task_Reject', 'Зафиксировать причину отказа', 2, 1, 2, 1)
node('End_Rejected', 'Перевозка отклонена', 2, 1, 3, 1, 'endEvent')
node('Task_Offer', 'Направить условия клиенту', 1, 2, 0, support='Согласуемая версия предложения')
node('Task_Approve', 'Рассмотреть предложение', 0, 2, 1)
node('Gateway_Approved', 'Условия приняты?', 0, 2, 2, kind='exclusiveGateway')
node('Gateway_Revise', 'Нужны изменения?', 0, 2, 3, 1, 'exclusiveGateway')
node('Task_Recalculate', 'Изменить расчёт и условия', 2, 2, 4, 1, support='Новая версия расчёта; прежнее согласование не переносится')
node('Task_Cancel', 'Зафиксировать отмену заказа', 1, 2, 4, 1)
node('End_Declined', 'Заказ отменён', 1, 2, 5, 1, 'endEvent')
node('Task_Assign', 'Назначить автомобиль и водителя', 3, 3, 0, support='Назначение ресурсов и план рейса')
node('Gateway_Assigned', 'Ресурсы назначены?', 3, 3, 1, kind='exclusiveGateway')
node('Task_Alternative', 'Подобрать другой транспорт или водителя', 3, 3, 2, 1)
node('Task_Route', 'Получить маршрут и документы', 4, 3, 2)
node('Task_Arrival', 'Прибыть на погрузку', 4, 3, 3)
node('Task_Load', 'Принять груз и начать рейс', 4, 3, 4, support='Фактическая погрузка, отметка «В пути»')
node('Task_Monitor', 'Контролировать рейс и события', 3, 4, 0, support='События, статусы и журнал инцидентов; GPS-интеграция не заявляется')
node('Gateway_Incident', 'Есть отклонение?', 3, 4, 1, kind='exclusiveGateway')
node('Task_Incident', 'Создать карточку инцидента', 3, 4, 2, 1)
node('Task_Resolve', 'Согласовать решение по инциденту', 3, 4, 3, 1)
node('Task_Continue', 'Продолжить рейс по согласованному решению', 4, 4, 4, 1,
     support='После продолжения рейса диспетчер повторно проверяет статус и события')
node('Gateway_Resolved', 'Отклонение устранено?', 4, 4, 5, 1,
     kind='exclusiveGateway',
     support='Да — вернуться к контролю рейса; Нет — повторно согласовать решение')
node('Task_Deliver', 'Доставить груз', 4, 4, 2)
node('Task_Proof', 'Получить подтверждение доставки', 4, 4, 3, support='Подписанная ТТН / УПД или электронное подтверждение')
node('Gateway_Claim', 'Есть претензия?', 1, 5, 0, kind='exclusiveGateway')
node('Task_Claim', 'Зарегистрировать претензию и доказательства', 1, 5, 1, 1)
node('Task_ClaimResolve', 'Обработать претензию и зафиксировать решение', 1, 5, 2, 1, support='Результат урегулирования; до него заказ не закрывается')
node('Task_Documents', 'Передать закрывающие документы', 4, 5, 2)
node('Task_Invoice', 'Проверить документы и выставить счёт', 5, 5, 3, support='Комплект документов, счёт и срок оплаты')
node('Task_Payment', 'Проверить оплату или передачу задолженности', 5, 5, 4, support='Основание закрытия согласно правилам Wiki')
node('Task_Close', 'Закрыть заказ', 5, 5, 5, support='Финальный статус после документов и урегулирования')
node('End_Closed', 'Заказ закрыт', 5, 5, 6, kind='endEvent')
for a,b in [('Start_Request','Task_Request'),('Task_Request','Task_Register'),('Task_Register','Gateway_Complete'),('Task_Ask','Task_Clarify'),('Task_Check','Gateway_Feasible'),('Task_Reject','End_Rejected'),('Task_Calculate','Task_Offer'),('Task_Offer','Task_Approve'),('Task_Approve','Gateway_Approved'),('Task_Cancel','End_Declined'),('Task_Assign','Gateway_Assigned'),('Task_Route','Task_Arrival'),('Task_Arrival','Task_Load'),('Task_Load','Task_Monitor'),('Task_Monitor','Gateway_Incident'),('Task_Incident','Task_Resolve'),('Task_Resolve','Task_Continue'),('Task_Continue','Gateway_Resolved'),('Task_Deliver','Task_Proof'),('Task_Proof','Gateway_Claim'),('Task_Claim','Task_ClaimResolve'),('Task_ClaimResolve','Task_Documents'),('Task_Documents','Task_Invoice'),('Task_Invoice','Task_Payment'),('Task_Payment','Task_Close'),('Task_Close','End_Closed')]: flow(a,b)
for a,b,label in [('Gateway_Complete','Task_Ask','Нет'),('Gateway_Complete','Task_Check','Да'),('Gateway_Feasible','Task_Reject','Нет'),('Gateway_Feasible','Task_Calculate','Да'),('Gateway_Approved','Gateway_Revise','Нет'),('Gateway_Approved','Task_Assign','Да'),('Gateway_Revise','Task_Recalculate','Да'),('Gateway_Revise','Task_Cancel','Нет'),('Gateway_Assigned','Task_Alternative','Нет'),('Gateway_Assigned','Task_Route','Да'),('Gateway_Incident','Task_Incident','Да'),('Gateway_Incident','Task_Deliver','Нет'),('Gateway_Resolved','Task_Resolve','Нет'),('Gateway_Claim','Task_Claim','Да'),('Gateway_Claim','Task_Documents','Нет')]: flow(a,b,label)
flow('Gateway_Resolved','Task_Monitor','Да',loop=True)
for a,b in [('Task_Clarify','Task_Register'),('Task_Recalculate','Task_Offer'),('Task_Alternative','Task_Assign')]: flow(a,b,loop=True)

def layout(phases, compact=False):
    selected={id:v for id,v in NODES.items() if v['phase'] in phases}
    lanes=sorted({v['lane'] for v in selected.values()}) if compact else list(range(6))
    offsets={}; x=180
    for phase in phases:
        offsets[phase]=x
        x += (max(v['col'] for v in selected.values() if v['phase']==phase)+1)*220+100
    lane_height=260 if compact else 360
    boxes={}
    for id,v in selected.items():
        w,h=(160,80) if v['kind']=='task' else (60,60)
        boxes[id]=(offsets[v['phase']]+v['col']*220,100+lanes.index(v['lane'])*lane_height+v['track']*120,w,h)
    if not compact:
        # Terminations sit UNDER their exceptional task, not in the horizontal
        # reading direction of the accepted route. They are not intermediate steps.
        for end,task in [('End_Rejected','Task_Reject'),('End_Declined','Task_Cancel')]:
            if end in boxes:
                tx,ty,tw,th=boxes[task]
                boxes[end]=(tx+50,ty+110,60,60)
    return selected,lanes,boxes,x+50,80+len(lanes)*lane_height

def port(box, side):
    x,y,w,h=box
    return {'L':(x,y+h//2),'R':(x+w,y+h//2),'T':(x+w//2,y),'B':(x+w//2,y+h)}[side]
def simplify(points):
    out=[]
    for p in points:
        if out and p==out[-1]: continue
        if len(out)>1 and ((out[-2][0]==out[-1][0]==p[0]) or (out[-2][1]==out[-1][1]==p[1])): out.pop()
        out.append(p)
    return out

def route(flow, boxes, width, height, occupied):
    a,b=flow['a'],flow['b']; A,B=boxes[a],boxes[b]
    # Distinct outgoing ports prevent a rejected/cancelled end from appearing
    # on the accepted path. End events never have an outgoing connector.
    exception_ports={'Gateway_Complete':'Да','Gateway_Feasible':'Нет',
                     'Gateway_Approved':'Нет','Gateway_Revise':'Да',
                     'Gateway_Assigned':'Нет','Gateway_Incident':'Да',
                     'Gateway_Resolved':'Да','Gateway_Claim':'Нет'}
    if a=='Task_Continue' and b=='Gateway_Resolved':
        sside='R'
    elif a=='Task_Ask' and b=='Task_Clarify':
        sside='R'
    elif a=='Gateway_Resolved' and b=='Task_Monitor' and flow['label']=='Да':
        sside='T'
    elif a=='Task_Clarify' and b=='Task_Register':
        sside='B'
    elif a=='Task_Recalculate' and b=='Task_Offer':
        sside='R'
    elif a=='Task_Proof' and b=='Gateway_Claim':
        sside='B'
    elif a=='Gateway_Complete' and b=='Task_Check':
        sside='B'
    elif a=='Gateway_Complete' and b=='Task_Ask':
        sside='R'
    elif a=='Gateway_Incident' and b=='Task_Incident' and flow['label']=='Да':
        sside='R'
    elif a=='Gateway_Incident' and b=='Task_Deliver' and flow['label']=='Нет':
        sside='B'
    elif a=='Task_Load' and b=='Task_Monitor':
        sside='R'
    elif a=='Gateway_Claim' and b=='Task_Claim' and flow['label']=='Да':
        sside='R'
    elif a=='Task_Alternative' and b=='Task_Assign' and flow['loop']:
        sside='L'
    elif a=='Task_ClaimResolve' and b=='Task_Documents':
        sside='B'
    elif a=='Task_Resolve' and b=='Task_Continue':
        sside='B'
    elif a=='Gateway_Resolved' and b=='Task_Resolve' and flow['label']=='Нет':
        sside='L'
    else:
        sside='B' if flow['loop'] or (a in exception_ports and flow['label']==exception_ports[a]) else 'R'
    gateway_branch=NODES[a]['kind']=='exclusiveGateway'
    if a=='Task_Continue' and b=='Gateway_Resolved':
        tside='B'
    elif a=='Task_Ask' and b=='Task_Clarify':
        tside='R'
    elif a=='Task_Clarify' and b=='Task_Register':
        tside='T'
    elif a=='Task_Recalculate' and b=='Task_Offer':
        tside='T'
    elif a=='Task_Proof' and b=='Gateway_Claim':
        tside='L'
    elif a=='Task_Documents' and b=='Task_Invoice':
        tside='T'
    elif a=='Gateway_Complete' and b=='Task_Check':
        tside='L'
    elif a=='Gateway_Complete' and b=='Task_Ask':
        tside='L'
    elif a=='Gateway_Incident' and b=='Task_Deliver' and flow['label']=='Нет':
        tside='L'
    elif a=='Gateway_Incident' and b=='Task_Incident' and flow['label']=='Да':
        tside='T'
    elif a=='Gateway_Claim' and b=='Task_Documents' and flow['label']=='Нет':
        tside='L'
    elif a=='Task_ClaimResolve' and b=='Task_Documents':
        tside='T'
    elif a=='Task_Resolve' and b=='Task_Continue':
        tside='T'
    elif a=='Gateway_Resolved' and b=='Task_Resolve' and flow['label']=='Нет':
        tside='R'
    elif a=='Task_Alternative' and b=='Task_Assign' and flow['loop']:
        tside='B'
    elif a=='Gateway_Resolved' and b=='Task_Monitor' and flow['label']=='Да':
        tside='T'
    elif flow['loop'] and NODES[b]['kind']=='exclusiveGateway':
        tside='B'
    else:
        tside='T' if (gateway_branch and NODES[b]['kind']=='task' and B[1]>A[1]) or (not flow['loop'] and NODES[b]['kind']=='endEvent' and B[1]>A[1]+A[3] and abs((A[0]+A[2]/2)-(B[0]+B[2]/2))<10) else 'L'
    start,end=port(A,sside),port(B,tside)
    delta={'R':(20,0),'L':(-20,0),'T':(0,-20),'B':(0,20)}
    # Keep the port selected for each XOR branch. Rewriting it to the bottom
    # whenever a task lies in a lower lane made both answers leave the same
    # gateway edge (most visibly at "Есть претензия?"). Non-gateway flows to
    # vertically placed end events may still use the bottom edge.
    if (tside=='T' and not gateway_branch and NODES[b]['kind']=='endEvent'
            and not (a=='Gateway_Resolved' and b=='Task_Resolve')
            and not (a=='Gateway_Revise' and flow['label']=='Нет')):
        sside='B'; start=port(A,sside)
    s=(start[0]+delta[sside][0],start[1]+delta[sside][1]); t=(end[0]+delta[tside][0],end[1]+delta[tside][1])

    def fixed(points):
        points=simplify(points)
        for p,q in zip(points,points[1:]):
            distance=max(abs(q[0]-p[0]),abs(q[1]-p[1]))
            steps=max(1,distance//10)
            for step in range(steps+1):
                occupied.add((p[0]+(q[0]-p[0])*step//steps,
                              p[1]+(q[1]-p[1])*step//steps))
        return points

    if a=='Gateway_Complete' and b=='Task_Check':
        # The accepted branch descends in the manager/logistics gap and enters
        # the check task from the left; it no longer forms a vertical barrier
        # across the client clarification loop.
        return fixed([start,s,(s[0],t[1]),t,end])
    if a=='Gateway_Complete' and b=='Task_Ask':
        # The incomplete-data branch exits right and enters the clarification
        # request from the left, with a short dogleg clear of the accepted path.
        corridor_x=t[0]-20
        return fixed([start,s,(corridor_x,s[1]),(corridor_x,t[1]),t,end])
    if a=='Gateway_Feasible' and b=='Task_Reject':
        # Rejection stays below the accepted route and enters its task from left.
        return fixed([start,s,(s[0],t[1]),t,end])
    if a=='Task_Load' and b=='Task_Monitor':
        # Move from the loading lane into monitoring from above, clear of the
        # long delivery-proof feedback line routed along the left margin.
        return fixed([start,s,(s[0],t[1]),t,end])
    if a=='Task_Documents' and b=='Task_Invoice':
        # Billing is below the documents task. Enter from its top, leaving its
        # right port for the subsequent payment-control task.
        return fixed([start,s,(t[0],s[1]),t,end])
    if a=='Gateway_Incident' and b=='Task_Incident' and flow['label']=='Да':
        # Keep the incident branch above the normal-delivery branch and enter
        # the incident task from its top edge, clear of its outgoing flow.
        task_right=B[0]+B[2]
        return fixed([start,s,(task_right+40,s[1]),
                      (task_right+40,t[1]),(t[0],t[1]),end])
    if a=='Gateway_Incident' and b=='Task_Deliver' and flow['label']=='Нет':
        # The no-deviation branch drops just left of delivery, then enters from
        # the left; the incident branch uses a separate gateway exit above.
        corridor_x=B[0]-40
        return fixed([start,s,(corridor_x,s[1]),
                      (corridor_x,t[1]),t,end])
    if a=='Task_Ask' and b=='Task_Clarify':
        # Use a dedicated upper-right corridor. Leaving from the task's right
        # edge avoids the transport-check row; keeping the vertical leg above
        # that row also prevents a long shared wall through the full pool.
        bypass_x=max(x+w for id,(x,y,w,h) in boxes.items()
                     if NODES[id]['phase']==0)+(360 if 'Task_Check' in boxes else 80)
        return fixed([start,s,(bypass_x,s[1]),(bypass_x,t[1]),t,end])
    if a=='Task_Clarify' and b=='Task_Register':
        # The completed request returns from the right and reaches registration
        # from above. Its upper corridor is separate from the request-out route.
        bypass_x=max(x+w for id,(x,y,w,h) in boxes.items()
                     if NODES[id]['phase']==0)+40
        # Stay above the gateway title as well as its branch lines.
        corridor_y=boxes['Gateway_Complete'][1]-40
        return fixed([start,s,(bypass_x,s[1]),(bypass_x,corridor_y),
                      (t[0],corridor_y),t,end])
    if a=='Task_Proof' and b=='Gateway_Claim':
        # Go below the incident loop and around the outer-right edge, then
        # approach the claim decision from above. The no-claim path now exits
        # directly to Documents, so the two routes stay in separate corridors.
        outer_x=max(x+w for x,y,w,h in boxes.values())+40
        clear_y=max(y+h for x,y,w,h in boxes.values())+40
        upper_y=B[1]-50
        return fixed([start,s,(s[0],clear_y),(outer_x,clear_y),
                      (outer_x,upper_y),(t[0],upper_y),t,end])
    if a=='Gateway_Claim' and b=='Task_Documents' and flow['label']=='Нет':
        # No bypasses claim handling down the clear column under the gateway and
        # enters Documents from the left, not through the billing route.
        return fixed([start,s,(s[0],t[1]),t,end])
    if a=='Gateway_Claim' and b=='Task_Claim' and flow['label']=='Да':
        # Yes takes the right-hand side and enters claim registration from top.
        corridor_x=B[0]-20
        return fixed([start,s,(corridor_x,s[1]),
                      (corridor_x,t[1]),t,end])
    if a=='Task_ClaimResolve' and b=='Task_Documents':
        # These tasks are column-aligned. A direct top-to-bottom handoff keeps
        # this incoming flow separate from the document task's right-side exit.
        return fixed([start,s,t,end])
    if a=='Task_Resolve' and b=='Task_Continue':
        # Enter Continue from above, leaving its right side for the next step.
        return fixed([start,s,(t[0],s[1]),t,end])
    if a=='Task_Continue' and b=='Gateway_Resolved':
        # Approach the question from below. The path first drops left of the
        # diamond, then passes under it and enters only through the bottom port.
        lower_y=B[1]+B[3]+40
        outer_x=B[0]+B[2]+20
        return fixed([start,s,(s[0],lower_y),(outer_x,lower_y),
                      (outer_x,t[1]),t,end])
    if a=='Gateway_Resolved' and b=='Task_Resolve' and flow['label']=='Нет':
        # No leaves left into the free corridor between the gateway and
        # Continue, then returns to the resolution task from its right side.
        outer_x=boxes['Task_Continue'][0]+boxes['Task_Continue'][2]+40
        return fixed([start,s,(outer_x,s[1]),
                      (outer_x,t[1]),t,end])
    if a=='Gateway_Resolved' and b=='Task_Monitor' and flow['label']=='Да':
        # Once resolved, return to monitoring from above; the alternative answer
        # exits left and returns to incident resolution through a separate port.
        outer_x=A[0]+A[2]+40
        upper_y=max(70,boxes['Task_Monitor'][1]-120)
        return fixed([start,s,(outer_x,s[1]),(outer_x,upper_y),
                      (t[0],upper_y),t,end])
    if a=='Task_Recalculate' and b=='Task_Offer':
        # Route below the current stage's tasks and enter the offer from above,
        # keeping the retry distinct from the outgoing offer-to-client flow.
        corridor_y=max(y+h for id,(x,y,w,h) in boxes.items()
                       if NODES[id]['phase']==2)+30
        return fixed([start,s,(s[0],corridor_y),(t[0],corridor_y),t,end])
    if a=='Task_Alternative' and b=='Task_Assign' and 'Task_Route' in boxes:
        # Return to assignment around the left edge of the transport lane;
        # the former right-side detour crossed the accepted route to pickup.
        corridor_y=max(y+h for x,y,w,h in boxes.values())+40
        bypass_x=B[0]-20
        return fixed([start,s,(bypass_x,s[1]),(bypass_x,corridor_y),
                      (end[0],corridor_y),t,end])
    # Search on a 10px orthogonal grid. All coordinates and task centers align.
    blocked=set()
    for id,(x,y,w,h) in boxes.items():
        # Label areas of gateways/events are obstacles too.
        top=y-35 if NODES[id]['kind']=='exclusiveGateway' and id!='Gateway_Incident' else y
        bottom=y+h+35 if NODES[id]['kind'].endswith('Event') else y+h
        for xx in range(x-10,x+w+11,10):
            for yy in range(top//10*10,bottom+11,10): blocked.add((xx,yy))
    blocked.discard(s); blocked.discard(t)
    queue=[(0,0,s,None)]; best={(s,None):0}; prev={}; goal=None
    while queue:
        _,cost,p,d=heapq.heappop(queue)
        if cost!=best.get((p,d)): continue
        if p==t: goal=(p,d); break
        for nd,(dx,dy) in enumerate([(10,0),(-10,0),(0,10),(0,-10)]):
            q=(p[0]+dx,p[1]+dy)
            if q in blocked or not(140<=q[0]<=width-10 and 70<=q[1]<=height-10): continue
            # Keep sequence-flow lines visually distinct. Penalize sharing or
            # crossing an already routed segment enough to choose a clean detour.
            nc=cost+10+(35 if d is not None and d!=nd else 0)+(10000 if q in occupied else 0)
            state=(q,nd)
            if nc<best.get(state,1e30):
                best[state]=nc; prev[state]=(p,d)
                heapq.heappush(queue,(nc+abs(q[0]-t[0])+abs(q[1]-t[1]),nc,q,nd))
    if goal is None: raise RuntimeError(f'Cannot route {a} -> {b}')
    chain=[]
    while goal in prev: chain.append(goal[0]); goal=prev[goal]
    chain.append(s); chain.reverse(); occupied.update(chain)
    return simplify([start]+chain+[end])

def draw(phases, filename, compact=False):
    selected, lanes, boxes, width,height=layout(phases,compact)
    paths={}; occupied=set()
    for f in sorted(FLOWS,key=lambda f:f['loop']):
        if f['a'] in selected and f['b'] in selected: paths[f['id']]=route(f,boxes,width,height,occupied)
    title=TITLES[phases[0]] if len(phases)==1 else 'Обработка заказа на перевозку'
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">', '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#355f50"/></marker></defs>',f'<rect width="{width}" height="{height}" fill="white"/>',f'<text x="20" y="32" font-family="Arial" font-size="22" font-weight="bold" fill="#173d31">BPMN 2.0 · {escape(title)}</text>']
    lane_height=260 if compact else 360
    for i,lane in enumerate(lanes):
        y=60+i*lane_height
        svg += [f'<rect x="10" y="{y}" width="{width-20}" height="{lane_height}" fill="{("#f1f6f2" if i%2==0 else "white")}" stroke="#bdcec3"/>',f'<text x="22" y="{y+32}" font-family="Arial" font-size="17" font-weight="bold" fill="#285e4c">{LANES[lane]}</text>']
    if not compact:
        for phase in phases:
            left=min(b[0] for id,b in boxes.items() if selected[id]['phase']==phase)
            svg.append(f'<text x="{left}" y="55" font-family="Arial" font-size="17" font-weight="bold" fill="#205f53">{phase+1:02} · {escape(TITLES[phase])}</text>')
        height+=45
        svg[0]=svg[0].replace(f'height="{height-45}"',f'height="{height}"').replace(f' {height-45}"',f' {height}"')
        svg[2]=svg[2].replace(f'height="{height-45}"',f'height="{height}"')
        svg.append(f'<text x="20" y="{height-15}" font-family="Arial" font-size="18" fill="#466355">Основной маршрут — толстая зелёная линия. Тонкие связи — альтернативы и возвраты. Оранжевые окончания — отказ / отмена, без продолжения.</text>')
    for f in FLOWS:
        if f['id'] not in paths: continue
        pts=paths[f['id']]
        main=(f['a'],f['b']) in set(zip(MAIN_ROUTE,MAIN_ROUTE[1:]))
        svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in pts)+f'" fill="none" stroke="{"#205f53" if main else "#7c8f86"}" stroke-width="{4 if main else 2}" marker-end="url(#arrow)"/>')
        if f['label']:
            x,y=pts[0]; vertical=pts[1][0]==x
            if f['a']=='Gateway_Resolved':
                gx,gy,gw,gh=boxes['Gateway_Resolved']
                if f['label']=='Да':
                    outer_x=gx+gw+40
                    upper_y=max(70,boxes['Task_Monitor'][1]-120)
                    label_x=outer_x+8
                    label_y=(upper_y+gy-20)//2
                else:
                    label_x=gx-35
                    label_y=gy+35
                svg.append(f'<text x="{label_x}" y="{label_y}" font-family="Arial" font-size="15" fill="#8a592b">{f["label"]}</text>')
            else:
                svg.append(f'<text x="{x+8}" y="{y+24 if vertical else y-10}" font-family="Arial" font-size="15" fill="#8a592b">{f["label"]}</text>')
    for id,v in selected.items():
        x,y,w,h=boxes[id]; name=v['name']; kind=v['kind']
        if kind=='task':
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="white" stroke="#2d7058" stroke-width="2"/>')
            lines=textwrap.wrap(name,19)
            for j,line in enumerate(lines): svg.append(f'<text x="{x+w/2}" y="{y+h/2+(j-(len(lines)-1)/2)*18+5}" text-anchor="middle" font-family="Arial" font-size="15" fill="#203b30">{escape(line)}</text>')
        elif kind=='exclusiveGateway':
            svg.append(f'<path d="M{x+30} {y}l30 30-30 30-30-30Z" fill="#fff8ea" stroke="#a57532" stroke-width="2"/><path d="M{x+20} {y+20}l20 20m0-20-20 20" stroke="#a57532" stroke-width="2"/>')
            if id=='Gateway_Incident':
                svg.append(f'<text x="{x+w+30}" y="{y-4}" font-family="Arial" font-size="14" fill="#664723">{escape(name)}</text>')
            else:
                svg.append(f'<text x="{x+30}" y="{y-12}" text-anchor="middle" font-family="Arial" font-size="14" fill="#664723">{escape(name)}</text>')
        else:
            exceptional=id in ['End_Rejected','End_Declined']
            svg.append(f'<circle cx="{x+30}" cy="{y+30}" r="28" fill="{"#fbf0e6" if exceptional else "white"}" stroke="{"#c6844d" if exceptional else "#2d7058"}" stroke-width="{4 if kind=="endEvent" else 2}"/><text x="{x+30}" y="{y+85}" text-anchor="middle" font-family="Arial" font-size="14" fill="#203b30">{escape(name)}</text>')
    if compact:
        incoming=[f for f in FLOWS if f['b'] in selected and f['a'] not in selected]
        outgoing=[f for f in FLOWS if f['a'] in selected and f['b'] not in selected]
        gateway_ports={
            'Gateway_Complete': {'Нет':'R','Да':'B'},
            'Gateway_Feasible': {'Нет':'B','Да':'R'},
            'Gateway_Approved': {'Нет':'B','Да':'R'},
            'Gateway_Revise': {'Да':'B','Нет':'R'},
            'Gateway_Assigned': {'Нет':'B','Да':'R'},
            'Gateway_Incident': {'Да':'R','Нет':'B'},
            'Gateway_Resolved': {'Нет':'R','Да':'T'},
            'Gateway_Claim': {'Нет':'B','Да':'R'},
        }
        for f in outgoing:
            side=gateway_ports.get(f['a'],{}).get(f['label'],'R')
            x,y=port(boxes[f['a']],side)
            dx,dy={'R':(75,0),'L':(-75,0),'T':(0,-75),'B':(0,75)}[side]
            svg.append(f'<path d="M{x} {y}l{dx} {dy}" fill="none" stroke="#355f50" stroke-width="2.4" marker-end="url(#arrow)"/>')
            label=(f['label']+' · ' if f['label'] else '')+f'этап {NODES[f["b"]]["phase"]+1}'
            lx=x+(12 if side=='R' else -75 if side=='L' else 10)
            ly=y+(-12 if side in ('R','L') else -82 if side=='T' else 92)
            svg.append(f'<text x="{lx}" y="{ly}" font-family="Arial" font-size="14" fill="#8a592b">{escape(label)}</text>')
        for f in incoming:
            x,y=port(boxes[f['b']],'L')
            svg.append(f'<path d="M{x-45} {y}h45" fill="none" stroke="#355f50" stroke-width="2.4" marker-end="url(#arrow)"/>')
        # Continuations are explanatory labels, not fictitious BPMN end events.
        descriptions=[]
        for f in incoming+outgoing:
            other=f['a'] if f in incoming else f['b']
            descriptions.append(('Вход: ' if f in incoming else 'Далее: ')+NODES[other]['name']+(f' ({f["label"]})' if f['label'] else ''))
        height+=40+len(descriptions)*24
        svg[0]=svg[0].replace(f'height="{height-40-len(descriptions)*24}"',f'height="{height}"').replace(f' {height-40-len(descriptions)*24}"',f' {height}"')
        for i,line in enumerate(descriptions): svg.append(f'<text x="20" y="{height-24*(len(descriptions)-i)}" font-family="Arial" font-size="15" fill="#466355">{escape(line)}</text>')
    svg.append('</svg>')
    (HERE/filename).write_text(''.join(svg),encoding='utf-8')
    return boxes,paths,width,height

def write_model(boxes,paths,width,height):
    root=ET.Element('{'+B+'}definitions',id='Definitions_AmurTrans',targetNamespace='https://petkras.github.io/amurtrans-kontrol/bpmn')
    collab=ET.SubElement(root,'{'+B+'}collaboration',id='Collaboration_Order')
    ET.SubElement(collab,'{'+B+'}participant',id='Participant_Order',name='АмурТранс — обработка заказа',processRef='Process_Order')
    proc=ET.SubElement(root,'{'+B+'}process',id='Process_Order',name='Обработка заказа на перевозку',isExecutable='false')
    ls=ET.SubElement(proc,'{'+B+'}laneSet',id='LaneSet_Order')
    for i,label in enumerate(LANES):
        lane=ET.SubElement(ls,'{'+B+'}lane',id=f'Lane_{i}',name=label)
        for id,v in NODES.items():
            if v['lane']==i: ET.SubElement(lane,'{'+B+'}flowNodeRef').text=id
    for id,v in NODES.items():
        el=ET.SubElement(proc,'{'+B+'}'+v['kind'],id=id,name=v['name'])
        if v['support']: ET.SubElement(el,'{'+B+'}documentation').text=v['support']+'. Ответственное лицо сохраняет право принятия решения.'
        for f in FLOWS:
            if f['b']==id: ET.SubElement(el,'{'+B+'}incoming').text=f['id']
        for f in FLOWS:
            if f['a']==id: ET.SubElement(el,'{'+B+'}outgoing').text=f['id']
    for f in FLOWS: ET.SubElement(proc,'{'+B+'}sequenceFlow',id=f['id'],sourceRef=f['a'],targetRef=f['b'],**({'name':f['label']} if f['label'] else {}))
    diagram=ET.SubElement(root,'{'+D+'}BPMNDiagram',id='Diagram_Order')
    plane=ET.SubElement(diagram,'{'+D+'}BPMNPlane',id='Plane_Order',bpmnElement='Collaboration_Order')
    def shape(id,box,**attrs):
        s=ET.SubElement(plane,'{'+D+'}BPMNShape',id='Shape_'+id,bpmnElement=id,**attrs)
        ET.SubElement(s,'{'+C+'}Bounds',**{k:str(v) for k,v in zip(['x','y','width','height'],box)})
    shape('Participant_Order',(0,60,width,height-60),isHorizontal='true')
    for i in range(6): shape(f'Lane_{i}',(30,60+i*360,width-30,360),isHorizontal='true')
    for id,box in boxes.items(): shape(id,box)
    for f in FLOWS:
        edge=ET.SubElement(plane,'{'+D+'}BPMNEdge',id='Edge_'+f['id'],bpmnElement=f['id'])
        for x,y in paths[f['id']]: ET.SubElement(edge,'{'+I+'}waypoint',x=str(x),y=str(y))
    ET.indent(root); ET.ElementTree(root).write(HERE/'order-process.bpmn',encoding='utf-8',xml_declaration=True)

def validate():
    outgoing=defaultdict(list); incoming=defaultdict(list)
    for f in FLOWS: outgoing[f['a']].append(f); incoming[f['b']].append(f)
    for id,v in NODES.items():
        if v['kind']=='endEvent': assert not outgoing[id]
        elif v['kind']=='exclusiveGateway': assert sorted(f['label'] for f in outgoing[id])==['Да','Нет']
        else: assert outgoing[id],id
        if v['kind']!='startEvent': assert incoming[id],id
    seen=set(); todo=['Start_Request']
    while todo:
        id=todo.pop()
        if id in seen: continue
        seen.add(id); todo.extend(f['b'] for f in outgoing[id])
    assert seen==set(NODES),set(NODES)-seen
    ends={id for id,v in NODES.items() if v['kind']=='endEvent'}; can_end=set(ends)
    while True:
        new=can_end|{f['a'] for f in FLOWS if f['b'] in can_end}
        if new==can_end: break
        can_end=new
    assert can_end==set(NODES)
    return dict(nodes=len(NODES),flows=len(FLOWS),lanes=LANES,reachable=True,no_outgoing_end_events=True,all_branches_named=True)

def main():
    results=validate()
    boxes,paths,w,h=draw(list(range(6)),'order-process.svg')
    assert all(x==X or y==Y for pts in paths.values() for (x,y),(X,Y) in zip(pts,pts[1:]))
    gateway_ports={}
    for gateway in (id for id,v in NODES.items() if v['kind']=='exclusiveGateway'):
        branches=[f for f in FLOWS if f['a']==gateway]
        sides=[]
        for branch in branches:
            start,next_point=paths[branch['id']][:2]
            side=('R' if next_point[0]>start[0] else
                  'L' if next_point[0]<start[0] else
                  'B' if next_point[1]>start[1] else 'T')
            sides.append((branch['label'],side))
        assert len(branches)==2 and len({side for _,side in sides})==2, (gateway,sides)
        gateway_ports[gateway]=dict(sides)
    write_model(boxes,paths,w,h)
    for i in range(6): draw([i],f'order-process-report-{i+1}.svg',True)
    draw([0,1,2],'order-process-part-1.svg'); draw([3,4,5],'order-process-part-2.svg')
    results['orthogonal_flows']=True
    results['distinct_gateway_ports']=gateway_ports
    (HERE/'validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False))
if __name__=='__main__': main()
