from django.conf import settings


def can_read_demo_inbox(request):
    return (
        settings.DEBUG
        and request.META.get("REMOTE_ADDR") in {"127.0.0.1", "::1"}
        and request.user.is_authenticated
        and request.user.is_superuser
    )


def demo_mode(request):
    return {"debug_demo": can_read_demo_inbox(request)}


# The first visible page in each section is its entry point.
APP_SECTIONS = (
    ("Dashboard", "dashboard", (
        ("Dashboard", "dashboard", ()),
    )),
    ("Fleet", "vehicles", (
        ("Vehicles", "vehicles", ("add_vehicle", "vehicle_detail", "edit_vehicle", "delete_vehicle")),
        ("Drivers", "drivers", ("add_drivers", "edit_drivers")),
        ("Routes", "routes", ("add_routes", "edit_routes")),
        ("Maintenance", "maintenance", ("record_service", "edit_service")),
    )),
    ("Operations", "dashboard", (
        ("Daily operations", "daily_operations", ("add_operation", "edit_operation", "operation_detail")),
        ("Assignments", "assignments", ("add_assignment", "edit_assignment")),
    )),
    ("Finance", "reports", (
        ("Collections", "collections", ("legacy_collections",)),
        ("Expenses", "expenses", ("add_expense", "edit_expense", "delete_expense")),
        ("Reports", "reports", ()),
    )),
)
MANAGER_PAGES = {"maintenance", "collections", "expenses", "reports"}


def app_navigation(request):
    match = request.resolver_match
    if not match or not request.user.is_authenticated:
        return {}
    current = match.url_name
    primary, secondary = [], []
    for label, icon, entries in APP_SECTIONS:
        pages = [
            {"label": name, "route": route,
             "current": "page" if current == route else "location" if current in related else ""}
            for name, route, related in entries
            if request.user.is_sacco_manager or route not in MANAGER_PAGES
        ]
        if not pages:
            continue
        active = any(page["current"] for page in pages)
        if active and len(pages) > 1:
            secondary = pages
        primary.append({
            "label": label, "icon": icon, "route": pages[0]["route"],
            "current": ("page" if current == pages[0]["route"] else "location") if active else "",
        })
    return {"app_sections": primary, "app_section_pages": secondary}
