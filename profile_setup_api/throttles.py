from rest_framework.throttling import UserRateThrottle


class ProfileCreateThrottle(UserRateThrottle):
    scope = 'profile_create'