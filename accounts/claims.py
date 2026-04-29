def jwt_custom_claims(user):
    return {
        "role": user.role,
        "email": user.email,
    }