"""Barber area - Manage Items & Services (CRUD)."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from bookings.decorators import barber_required
from bookings.models import Service


@barber_required
def services(request):
    return render(request, "barber/services.html",
                  {"services": Service.objects.all()})


@barber_required
def service_new(request):
    if request.method == "POST":
        return _save_service(request, None)
    return render(request, "barber/service_form.html",
                  {"service": None, "action": "new"})


@barber_required
def service_edit(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    if request.method == "POST":
        return _save_service(request, service)
    return render(request, "barber/service_form.html",
                  {"service": service, "action": "edit"})


def _save_service(request, service):
    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()
    image = request.POST.get("image", "").strip()
    active = request.POST.get("active") == "on"

    errors = []
    if not name:
        errors.append("Service name is required.")
    try:
        duration = int(request.POST.get("duration_minutes", "0"))
        if duration <= 0:
            raise ValueError
    except ValueError:
        errors.append("Duration must be a positive whole number of minutes.")
        duration = 30
    try:
        price = float(request.POST.get("price", "0"))
        if price < 0:
            raise ValueError
    except ValueError:
        errors.append("Price must be a valid non-negative number.")
        price = 0.0

    if errors:
        for e in errors:
            messages.error(request, e)
        draft = service or Service()
        draft.name, draft.description = name, description
        draft.duration_minutes, draft.price = duration, price
        draft.image, draft.active = image, active
        action = "edit" if service else "new"
        return render(request, "barber/service_form.html",
                      {"service": draft, "action": action})

    if service is None:
        service = Service()
    service.name = name
    service.description = description
    service.duration_minutes = duration
    service.price = price
    service.image = image or "default.svg"
    service.active = active
    service.save()
    messages.success(request, "Service saved.")
    return redirect("barber_services")


@barber_required
def service_delete(request, service_id):
    if request.method != "POST":
        return redirect("barber_services")
    service = get_object_or_404(Service, pk=service_id)
    service.delete()
    messages.success(request, "Service deleted.")
    return redirect("barber_services")
