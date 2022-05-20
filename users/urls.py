from django.urls import path
from users.views import LoginFormView, RegistrationFormView, \
    LogoutFormView, UserProfileTemplateView, UserProfileFormView, UserVerifyView, \
    UserPasswordRecoveryFormView, UserSetPasswordFormView, UserFriendsTemplateView, \
    UserFriendRequest, UserFriendVerify, UserFriendDelete

app_name = 'users'

urlpatterns = [
    path('login/', LoginFormView.as_view(), name='login'),
    path('register/', RegistrationFormView.as_view(), name='register'),
    path('profile/', UserProfileFormView.as_view(), name='myprofile'),
    path('friends/<int:id>/', UserFriendsTemplateView.as_view(), name='myfriends'),
    path('<int:id>/', UserProfileTemplateView.as_view(), name='usersprofile'),
    path('friend_request/<int:obj>/', UserFriendRequest.as_view(), name='friend_request'),
    path('friend_verify/<int:from>/<int:to>/', UserFriendVerify.as_view(), name='friend_verify'),
    path('friend_delete/<int:from>/<int:to>/', UserFriendDelete.as_view(), name='friend_delete'),
    path('logout/', LogoutFormView.as_view(), name='logout'),
    path('verify/<str:username>/<str:activation_key>/',
         UserVerifyView.as_view(), name='verify'),
    path('password-recovery/', UserPasswordRecoveryFormView.as_view(),
         name='password-recovery'),
    path('password-recovery-link/<str:email>/<str:password_recovery_key>/',
         UserSetPasswordFormView.as_view(), name='password-recovery-link'),
]
