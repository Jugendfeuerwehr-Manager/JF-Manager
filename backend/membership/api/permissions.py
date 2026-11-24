from jf_manager_backend.permissions import DepartmentRoleModelPermissions


class MemberRightsPermissions(DepartmentRoleModelPermissions):
    """Movements belong to the member record: reading and correcting them uses the member rights."""

    perms_map = {
        "GET": ["members.view_member"],
        "OPTIONS": [],
        "HEAD": [],
        "PUT": ["members.change_member"],
        "PATCH": ["members.change_member"],
    }
