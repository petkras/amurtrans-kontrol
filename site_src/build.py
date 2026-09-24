"""Build the static AmurTrans knowledge base for GitHub Pages."""

from __future__ import annotations

import html
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "02-wiki" / "source-vault"
HERE = Path(__file__).resolve().parent
OUTPUT = ROOT / "site"


@dataclass(frozen=True)
class Page:
    slug: str
    title: str
    group: str
    source: str
    summary: str
    status: str = "Концепция продукта"


PAGES = [
    Page("product-definition", "Определение продукта", "Продукт", "01_Продукт/01_Определение продукта.md", "Проблема, аудитория, ценность и границы решения."),
    Page("product-state", "Состояние и KPI", "Продукт", "01_Продукт/02_Состояние продукта.md", "Этап проекта, целевые показатели и способ измерения."),
    Page("product-roadmap", "Развитие продукта", "Продукт", "01_Продукт/03_Развитие продукта.md", "Приоритеты, этапы и ближайшие цели развития."),
    Page("product-backlog", "Продуктовая очередь", "Продукт", "01_Продукт/04_Продуктовая очередь.md", "Функции, гипотезы и критерии завершения."),
    Page("product-artifacts", "Артефакты", "Продукт", "01_Продукт/05_Артефакты.md", "Схемы, макеты и другие проверяемые материалы."),
    Page("product-roles", "Роли и ответственность", "Продукт", "02_Справочники/01_Роли и ответственность.md", "Участники процесса и матрица ответственности."),
    Page("process-map", "Карта процесса", "Процесс", "01_Процесс/01_Карта процесса.md", "Путь заказа и правила перехода между статусами."),
    Page("process-intake", "Приём заявки", "Процесс", "01_Процесс/02_Приём заявки.md", "Входные данные и первичная регистрация заказа."),
    Page("process-check", "Проверка и расчёт", "Процесс", "01_Процесс/03_Проверка и расчёт.md", "Проверка реализуемости, стоимости и условий."),
    Page("process-plan", "Планирование перевозки", "Процесс", "01_Процесс/04_Планирование перевозки.md", "Назначение транспорта и подготовка рейса."),
    Page("process-execution", "Исполнение и контроль", "Процесс", "01_Процесс/05_Исполнение и контроль.md", "События рейса, отклонения и связь с клиентом."),
    Page("process-close", "Закрытие заказа", "Процесс", "01_Процесс/06_Закрытие заказа.md", "Подтверждение доставки и завершающие действия."),
    Page("process-scenarios", "Сценарии обработки", "Процесс", "01_Процесс/07_Сценарии обработки.md", "Основной путь и исключения процесса."),
    Page("data-order", "Данные заказа", "Данные", "02_Справочники/02_Данные заказа.md", "Состав карточки заказа и правила качества данных."),
    Page("data-documents", "Документы", "Данные", "02_Справочники/03_Документы.md", "Документы и контроль их прохождения по этапам."),
    Page("data-tariff", "Тариф и допуслуги", "Данные", "02_Справочники/05_Тариф и допуслуги.md", "Концептуальная логика стоимости перевозки."),
    Page("data-model", "Модель данных", "Данные", "02_Справочники/06_Модель данных и интеграции.md", "Сущности, связи и границы внешних интеграций."),
    Page("data-glossary", "Глоссарий", "Данные", "02_Справочники/04_Глоссарий.md", "Единые определения терминов продукта."),
    Page("ops-kpi", "KPI процесса", "Управление", "03_Управление/01_KPI.md", "Метрики процесса, формулы и действия при отклонении."),
    Page("ops-rules", "Правила и исключения", "Управление", "03_Управление/02_Правила и исключения.md", "Изменения условий, инциденты и эскалация."),
    Page("ops-communication", "Коммуникации с клиентом", "Управление", "03_Управление/03_Коммуникации с клиентом.md", "События, о которых клиенту важно знать."),
    Page("ops-audit", "Контроль заказа", "Управление", "03_Управление/04_Чек лист аудита заказа.md", "Проверки по этапам заказа."),
    Page("ops-sla", "SLA процесса", "Управление", "03_Управление/05_SLA процесса.md", "Целевые сроки реакции на события процесса."),
    Page("ops-risks", "Риски", "Управление", "03_Управление/06_Реестр рисков.md", "Риски заказа и меры реагирования."),
    Page("ops-access", "Доступ и права", "Управление", "03_Управление/07_Доступ и безопасность.md", "Кто может просматривать и изменять данные."),
    Page("tech-requirements", "Требования", "Техническая часть", "04_Техническая/01_Программные и аппаратные требования.md", "Требования к Wiki и целевому продукту."),
    Page("tech-architecture", "Архитектура", "Техническая часть", "04_Техническая/02_Архитектура продукта.md", "Компоненты системы, связи и архитектурные решения."),
    Page("tech-testing", "Тестирование", "Техническая часть", "04_Техническая/03_Тестирование.md", "Набор проверок будущего функционала и Wiki."),
    Page("tech-security", "Безопасность", "Техническая часть", "04_Техническая/04_Безопасность.md", "Угрозы, права и защита информации."),
    Page("tech-backlog", "Техническая очередь", "Техническая часть", "04_Техническая/05_Техническая очередь.md", "Технические задачи и критерии готовности."),
    Page("tech-on-call", "Регламент поддержки", "Техническая часть", "04_Техническая/07_Дежурства.md", "Плановая модель сопровождения продукта."),
    Page("case-order", "Сквозной пример заказа", "Примеры и материалы", "05_Примеры/01_Сквозной пример заказа.md", "Учебный пример прохождения заказа по всем этапам."),
    Page("case-claim", "Пример претензии", "Примеры и материалы", "05_Примеры/02_Разбор претензии.md", "Учебный случай отклонения при перевозке."),
    Page("ai-usage", "Применение ИИ", "Примеры и материалы", "04_AI/01_Применение ИИ.md", "Как применялся ИИ при подготовке Wiki."),
    Page("course-materials", "Материалы курса", "Примеры и материалы", "@materials.md", "Лабораторные материалы и исходные артефакты."),
]

GROUPS = ["Продукт", "Процесс", "Данные", "Управление", "Техническая часть", "Примеры и материалы"]
GROUP_LEADS = {
    "Продукт": "product-definition",
    "Процесс": "process-map",
    "Данные": "data-order",
    "Управление": "ops-kpi",
    "Техническая часть": "tech-architecture",
    "Примеры и материалы": "course-materials",
}


def source_path(page: Page) -> Path:
    return HERE / "content" / page.source[1:] if page.source.startswith("@") else SOURCE / page.source


BY_SOURCE = {source_path(page).resolve(): page for page in PAGES}
BY_STEM = {source_path(page).stem: page for page in PAGES}


def resolve_wikilink(source: Path, target: str) -> Page | None:
    raw = target.split("#", 1)[0]
    candidate = Path(raw)
    variants = [source.parent / candidate, SOURCE / candidate]
    for path in variants:
        if path.suffix == "":
            path = path.with_suffix(".md")
        found = BY_SOURCE.get(path.resolve())
        if found:
            return found
    return BY_STEM.get(candidate.stem)


def prepare_markdown(page: Page, raw: str) -> str:
    raw = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", raw, flags=re.S)
    raw = re.sub(r"\A#\s+[^\n]+\n", "", raw)
    source = source_path(page)

    def replace_wikilink(match: re.Match[str]) -> str:
        is_image = match.group(1) == "!"
        target, _, label = match.group(2).partition("|")
        target = target.strip()
        if is_image:
            filename = Path(target).name
            alt = label.strip() or Path(filename).stem.replace("_", " ")
            return f"![{alt}](assets/{filename})"
        linked = resolve_wikilink(source, target)
        caption = label.strip() or (linked.title if linked else Path(target).stem.replace("_", " "))
        return f"[{caption}]({linked.slug}.html)" if linked else caption

    raw = re.sub(r"(!?)\[\[([^\]]+)\]\]", replace_wikilink, raw)
    diagram = {"tech-architecture": "architecture.svg", "data-model": "data-model.svg", "process-scenarios": "scenario.svg"}.get(page.slug)
    if diagram:
        raw = re.sub(r"```mermaid\s*\n.*?\n```", f"![Схема: {page.title}](assets/{diagram})", raw, flags=re.S)
    if page.slug == "process-map":
        raw = "![Схема сквозного процесса обработки заказа](assets/process.svg)\n\n" + raw
    if page.slug == "product-state":
        raw = """> **Статус данных.** Показатели ниже являются целевыми значениями для проектируемого продукта. Фактической статистики перевозок пока нет.\n\n""" + raw
    if page.slug == "ops-kpi":
        raw = """> **Целевые показатели.** Формулы определяют будущие измерения, а значения задают ориентир. Это не результат работающей компании.\n\n""" + raw
    return raw


def copy_assets() -> None:
    assets = OUTPUT / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for source in (HERE / "assets").iterdir():
        if source.is_file():
            shutil.copy2(source, assets / source.name)
    for source in (SOURCE / "assets").glob("*"):
        if source.is_file() and source.suffix.lower() != ".png":
            shutil.copy2(source, assets / source.name)
    homework = ROOT / "docs" / "02-wiki" / "homework" / "Интеллект_карта_Wiki_технологии.png"
    if homework.exists():
        shutil.copy2(homework, assets / "mindmap-wiki.png")
    bpmn = ROOT / "docs" / "03-bpmn" / "homework" / "Интеллект_карта_BPMN_2_0.png"
    if bpmn.exists():
        shutil.copy2(bpmn, assets / "mindmap-bpmn.png")


def label_tables(content: str, page: Page) -> str:
    """Give every table a visible, contextual caption."""
    count = 0
    heading = page.title
    parts = re.split(r"(<h[23][^>]*>.*?</h[23]>|<table>)", content, flags=re.S)
    for index, part in enumerate(parts):
        if re.match(r"<h[23]", part):
            heading = html.unescape(re.sub(r"<[^>]+>", "", part)).strip()
        elif part == "<table>":
            count += 1
            caption = html.escape(f"Таблица {count} — {heading}")
            parts[index] = f'<table><caption>{caption}</caption>'
    return "".join(parts)


def build() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    copy_assets()
    environment = Environment(loader=FileSystemLoader(HERE), autoescape=select_autoescape(["html"]))
    template = environment.get_template("template.html")
    search_index: list[dict[str, str]] = []
    groups = {group: [page for page in PAGES if page.group == group] for group in GROUPS}
    navigation = [{"name": group, "lead": GROUP_LEADS[group] + ".html", "pages": groups[group]} for group in GROUPS]
    rendered_pages: list[dict] = []
    for index, page in enumerate(PAGES):
        raw = source_path(page).read_text(encoding="utf-8-sig")
        md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"])
        content = label_tables(md.convert(prepare_markdown(page, raw)), page)
        toc = md.toc if "<li>" in md.toc else ""
        plain = html.unescape(re.sub(r"<[^>]+>", " ", content))
        plain = re.sub(r"\s+", " ", plain).strip()
        search_index.append({"title": page.title, "group": page.group, "url": page.slug + ".html", "summary": page.summary, "text": plain[:4500]})
        rendered_pages.append({"page": page, "content": content, "toc": toc, "index": index})
    search_json = json.dumps(search_index, ensure_ascii=False).replace("<", "\\u003c")
    for item in rendered_pages:
        page = item["page"]
        idx = item["index"]
        previous = PAGES[idx - 1] if idx > 0 else None
        following = PAGES[idx + 1] if idx + 1 < len(PAGES) else None
        result = template.render(home=False, title=page.title, summary=page.summary, page=page, content=item["content"], toc=item["toc"], navigation=navigation, search_json=search_json, previous=previous, following=following)
        (OUTPUT / f"{page.slug}.html").write_text(result, encoding="utf-8")
    home = template.render(home=True, title="АмурТранс Контроль", summary="База знаний продукта для обработки заказов транспортной компании.", page=None, content="", toc="", navigation=navigation, search_json=search_json, previous=None, following=None)
    (OUTPUT / "index.html").write_text(home, encoding="utf-8")
    (OUTPUT / "search-index.json").write_text(json.dumps(search_index, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built {len(PAGES) + 1} pages in {OUTPUT}")


if __name__ == "__main__":
    build()
