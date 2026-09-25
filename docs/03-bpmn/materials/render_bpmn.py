"""Lay out the source BPMN consistently and export a readable SVG preview."""
from __future__ import annotations

from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "order-process.bpmn"
OUT = HERE / "order-process.svg"
BN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
DI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
DD = "http://www.omg.org/spec/DD/20100524/DI"
ET.register_namespace("", BN)
ET.register_namespace("bpmndi", DI)
ET.register_namespace("dc", DC)
ET.register_namespace("di", DD)

# Horizontal order follows the main scenario. Lane index reflects responsibility.
LAYOUT = {
    "Start_Request": (80, 0), "Task_Request": (190, 0), "Task_Register": (380, 1),
    "Gateway_Complete": (560, 1), "Task_Ask": (700, 1), "Task_Clarify": (850, 0),
    "Task_Check": (1060, 2), "Gateway_Feasible": (1250, 2), "End_Rejected": (1390, 2),
    "Task_Calculate": (1510, 2), "Task_Offer": (1690, 1), "Task_Approve": (1860, 0),
    "Gateway_Approved": (2040, 0), "End_Declined": (2180, 0),
    "Task_Assign": (2300, 3), "Task_Load": (2490, 4), "Task_Monitor": (2680, 3),
    "Gateway_Incident": (2860, 3), "Task_Resolve": (3000, 3),
    "Task_Deliver": (3180, 4), "Task_Documents": (3380, 5),
    "Task_Close": (3570, 5), "End_Closed": (3740, 5),
}
LANES = ["Клиент", "Менеджер", "Логист", "Диспетчер", "Водитель", "Бухгалтер"]
Y0, STEP, HEIGHT = 102, 128, 72
W = 3960


def size(tag: str) -> tuple[int, int]:
    if tag.endswith("Gateway"):
        return 56, 56
    if tag.endswith("Event"):
        return 48, 48
    return 148, 68


def main() -> None:
    tree = ET.parse(SOURCE)
    root = tree.getroot()
    for old in root.findall(f"{{{DI}}}BPMNDiagram"):
        root.remove(old)
    process = root.find(f"{{{BN}}}process")
    assert process is not None
    by_id = {node.get("id"): node for node in process.iter() if node.get("id")}
    diagram = ET.SubElement(root, f"{{{DI}}}BPMNDiagram", id="Diagram_Order")
    plane = ET.SubElement(diagram, f"{{{DI}}}BPMNPlane", id="Plane_Order", bpmnElement="Collaboration_Order")
    pool = ET.SubElement(plane, f"{{{DI}}}BPMNShape", id="Shape_Participant", bpmnElement="Participant_Order", isHorizontal="true")
    ET.SubElement(pool, f"{{{DC}}}Bounds", x="0", y="0", width=str(W), height="840")
    for index, lane in enumerate(process.find(f"{{{BN}}}laneSet")):
        shape = ET.SubElement(plane, f"{{{DI}}}BPMNShape", id=f"Shape_{lane.get('id')}", bpmnElement=lane.get("id"), isHorizontal="true")
        ET.SubElement(shape, f"{{{DC}}}Bounds", x="0", y=str(62 + index * STEP), width=str(W), height=str(STEP))
    boxes = {}
    for node_id, (x, lane) in LAYOUT.items():
        node = by_id[node_id]
        w, h = size(node.tag.split("}")[-1])
        y = Y0 + lane * STEP + (HEIGHT - h) // 2
        boxes[node_id] = (x, y, w, h)
        shape = ET.SubElement(plane, f"{{{DI}}}BPMNShape", id=f"Shape_{node_id}", bpmnElement=node_id)
        ET.SubElement(shape, f"{{{DC}}}Bounds", x=str(x), y=str(y), width=str(w), height=str(h))
    paths = {}
    for flow in process.findall(f"{{{BN}}}sequenceFlow"):
        source, target = boxes[flow.get("sourceRef")], boxes[flow.get("targetRef")]
        x1, y1 = source[0] + source[2], source[1] + source[3] / 2
        x2, y2 = target[0], target[1] + target[3] / 2
        if x2 <= x1:
            # Explicit return loops are routed above the lanes.
            top = 55 if flow.get("id") == "F06" else 75 + 3 * STEP
            points = [(x1, y1), (x1 + 25, y1), (x1 + 25, top), (x2 - 25, top), (x2 - 25, y2), (x2, y2)]
        elif abs(y2 - y1) > STEP:
            mid = (x1 + x2) / 2
            points = [(x1, y1), (mid, y1), (mid, y2), (x2, y2)]
        else:
            points = [(x1, y1), (x2, y2)]
        paths[flow.get("id")] = points
        edge = ET.SubElement(plane, f"{{{DI}}}BPMNEdge", id=f"Edge_{flow.get('id')}", bpmnElement=flow.get("id"))
        for x, y in points:
            ET.SubElement(edge, f"{{{DD}}}waypoint", x=str(x), y=str(y))
    tree.write(SOURCE, encoding="utf-8", xml_declaration=True)

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="840" viewBox="0 0 {W} 840" role="img" aria-label="BPMN 2.0: обработка заказа на перевозку">',
           '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#54736a"/></marker></defs>',
           '<rect width="100%" height="100%" fill="#f8faf7"/><text x="24" y="35" font-family="Arial" font-size="22" font-weight="700" fill="#183d34">BPMN 2.0 · Обработка заказа на перевозку</text>']
    for i, label in enumerate(LANES):
        y = 62 + i * STEP
        svg.append(f'<rect x="12" y="{y}" width="{W-24}" height="{STEP}" fill="{("#f0f6f1" if i%2==0 else "#fff")}" stroke="#cbdcd0"/>')
        svg.append(f'<text x="23" y="{y+67}" font-family="Arial" font-size="15" font-weight="700" fill="#1f5f4d">{label}</text>')
    for flow in process.findall(f"{{{BN}}}sequenceFlow"):
        points = paths[flow.get("id")]
        svg.append('<polyline points="' + ' '.join(f'{x},{y}' for x, y in points) + '" fill="none" stroke="#54736a" stroke-width="2.2" marker-end="url(#arrow)"/>')
        if flow.get("name"):
            x, y = points[-2]
            svg.append(f'<text x="{x+5}" y="{y-8}" font-family="Arial" font-size="11" fill="#a35e1e">{flow.get("name")}</text>')
    for node_id, (x, y, w, h) in boxes.items():
        node = by_id[node_id]
        tag = node.tag.split("}")[-1]
        name = escape(node.get("name") or "")
        if tag == "exclusiveGateway":
            svg.append(f'<path d="M{x+w/2} {y} L{x+w} {y+h/2} L{x+w/2} {y+h} L{x} {y+h/2}Z" fill="#fff6e6" stroke="#ab7426" stroke-width="2"/>')
            svg.append(f'<path d="M{x+19} {y+19}l18 18m0-18l-18 18" stroke="#ab7426" stroke-width="2"/>')
            svg.append(f'<text x="{x+w/2}" y="{y-7}" text-anchor="middle" font-family="Arial" font-size="12" fill="#744b19">{name}</text>')
        elif tag.endswith("Event"):
            svg.append(f'<circle cx="{x+w/2}" cy="{y+h/2}" r="{w/2-2}" fill="white" stroke="#276b57" stroke-width="{3 if tag=="endEvent" else 2}"/>')
            svg.append(f'<text x="{x+w/2}" y="{y+h+17}" text-anchor="middle" font-family="Arial" font-size="11" fill="#33584b">{name}</text>')
        else:
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#fff" stroke="#2f7a65" stroke-width="2"/>')
            words = name.split()
            lines = [" ".join(words[:len(words)//2]), " ".join(words[len(words)//2:])] if len(words) > 3 else [name]
            for i, line in enumerate(lines):
                svg.append(f'<text x="{x+w/2}" y="{y+h/2 + (i-(len(lines)-1)/2)*17+4}" text-anchor="middle" font-family="Arial" font-size="11.5" fill="#223c32">{line}</text>')
    svg.append('</svg>')
    OUT.write_text("".join(svg), encoding="utf-8")
    whole = "".join(svg)
    for part, left, width in [(1, 0, 2040), (2, 1970, 1990)]:
        preview = whole.replace(f'width="{W}" height="840" viewBox="0 0 {W} 840"', f'width="{width}" height="840" viewBox="{left} 0 {width} 840"', 1)
        (HERE / f"order-process-part-{part}.svg").write_text(preview, encoding="utf-8")
    for part, left, width in [(1, 0, 1100), (2, 970, 1100), (3, 1970, 1100), (4, 2850, 1110)]:
        preview = whole.replace(f'width="{W}" height="840" viewBox="0 0 {W} 840"', f'width="{width}" height="840" viewBox="{left} 0 {width} 840"', 1)
        (HERE / f"order-process-report-{part}.svg").write_text(preview, encoding="utf-8")
    print(f"Updated {SOURCE} and {OUT}")


if __name__ == "__main__":
    main()
