from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpRequest

from apps.authentication.models.mfa_device import MFABackupCode, MFADevice
from apps.authentication.models.user_profile import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "is_staff", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Helix identity", {"fields": ("helix_sub",)}),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    readonly_fields = ["created_at", "updated_at", "last_login", "helix_sub"]


class MFABackupCodeInline(admin.TabularInline):
    model = MFABackupCode
    extra = 0
    can_delete = False
    fields = ["used_at", "created_at"]
    readonly_fields = ["used_at", "created_at"]

    def has_add_permission(self, request: HttpRequest, obj: MFADevice | None = None) -> bool:
        return False


@admin.register(MFADevice)
class MFADeviceAdmin(admin.ModelAdmin):
    ordering = ["-created_at"]
    list_display = ["user", "confirmed_at", "created_at"]
    search_fields = ["user__email"]
    readonly_fields = ["user", "confirmed_at", "created_at", "updated_at"]
    inlines = [MFABackupCodeInline]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
