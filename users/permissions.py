from rest_framework import permissions


def _has_role(request, role):
    user = request.user
    return bool(user and user.is_authenticated and user.is_active and user.role == role)


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return _has_role(request, 'ADMIN')


class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return _has_role(request, 'CUSTOMER')


class IsDealer(permissions.BasePermission):
    """Any dealer account, whatever its application status."""

    def has_permission(self, request, view):
        return _has_role(request, 'DEALER')


class IsApprovedDealer(permissions.BasePermission):
    """A dealer whose application is approved and who has not been deactivated."""

    message = 'Your dealer account is not approved or has been deactivated.'

    def has_permission(self, request, view):
        if not _has_role(request, 'DEALER'):
            return False
        profile = getattr(request.user, 'dealerprofile', None)
        return bool(profile and profile.status == 'APPROVED' and profile.is_active)
