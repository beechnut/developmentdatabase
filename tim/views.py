from django.shortcuts import render_to_response, redirect
from django.template  import RequestContext
from django.http      import Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.contrib import messages
from django.utils.functional import wraps
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.gis.geos        import GEOSGeometry
from django.core.exceptions         import FieldError

from development.models import Municipality, Project
from tim.models import ModeratedProject



def correct_municipal_user_or_staff(view):
    """
    Checks to see if the user:
        1) is not anonymous (aka logged in)
        2) is a Municipal User and thus has the power to moderate
        3) is viewing their own municipality.
    If so, it returns to the view the municipality object, from which
    the pending projects may be obtained.
    """
    @wraps(view)
    def inner(request, municipality_name, *args, **kwargs):

        user = request.user
        municipality_name = municipality_name.capitalize()

        if not user.is_staff:
            if user.is_anonymous():
                return HttpResponseForbidden("Log in as a Municipal User to access moderation.")

            if not user.profile.is_municipal:
                return HttpResponseForbidden("You are not a Municipal User. If you see this message in error, please contact MAPC.")

            if user.profile.municipality.name != municipality_name:
                return HttpResponseForbidden("You may not view other municipalities' pending edits.")

        try:
            municipality = Municipality.objects.get(name=municipality_name)
        except Municipality.DoesNotExist:
            return Http404

        return view(request, municipality, *args, **kwargs)

    return inner



def user_who_may_moderate(view):
    """
    Checks to see if the user:
        1) is not anonymous (aka logged in)
        2) is a Municipal User and thus has the power to moderate
        3) is moderating a post belonging to their municipality.
    If so, it accepts or declines the edit.
    """
    @wraps(view)
    def inner(request, project, *args, **kwargs):

        try:
            moderated_project = ModeratedProject.objects.get(object_id=project)
        except ModeratedProject.DoesNotExist:
            return Http404

        user = request.user
        
        if not user.is_staff:
            if user.is_anonymous():
                return HttpResponseForbidden("Log in as a Municipal User to access moderation.")

            if not user.profile.is_municipal:
                return HttpResponseForbidden("You are not a Municipal User. If you see this message in error, please contact MAPC.")

            if user.profile.municipality.name != moderated_project.municipality.name:
                return HttpResponseForbidden("You may not moderate other municipalities' pending edits.") 

        return view(request, moderated_project, *args, **kwargs)

    return inner





@staff_member_required
def all(request):
    """List all projects awaiting moderation"""

    pending_projects = ModeratedProject.objects.filter(completed=False)

    return render_to_response('all.html', locals(), context_instance=RequestContext(request))
    

@correct_municipal_user_or_staff
def municipality(request, municipality):
    """
    List a municipality's projects awaiting moderation.
    Available only to Municipal Users of the given municipality.
    """
    pending_projects = ModeratedProject.objects.filter(completed=False, taz__municipality__name=municipality.name)

    return render_to_response('municipality.html', locals(), context_instance=RequestContext(request))


# TODO: Uncomment, hook this up to the ModeratedProject / Project workflow
# @user_who_may_moderate
def accept(request, project):
    project = {'name': 'Elm St., #325'}    
    
    # project.accept()
    messages.add_message(request, messages.INFO, 'You accepted changes to %s.' % (project['name']))
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


# @user_who_may_moderate
def decline(request, project):
    project = {'name': 'Elm St., #325'}
    
    # project.decline()
    messages.add_message(request, messages.INFO, 'You declined changes to %s.' % (project['name']))
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

