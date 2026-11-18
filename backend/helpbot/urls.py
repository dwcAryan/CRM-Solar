from django.urls import path
from .views import (
    HelpbotAskView,
    HelpbotSuggestionsView,
    HelpbotFeedbackView,
    HelpbotUnansweredView,
    HelpbotStatsView,
    HelpbotRebuildIndexView,
)

urlpatterns = [
    path('ask/', HelpbotAskView.as_view(), name='helpbot-ask'),
    path('suggestions/', HelpbotSuggestionsView.as_view(), name='helpbot-suggestions'),
    path('feedback/', HelpbotFeedbackView.as_view(), name='helpbot-feedback'),
    path('unanswered/', HelpbotUnansweredView.as_view(), name='helpbot-unanswered'),
    path('unanswered/<int:pk>/', HelpbotUnansweredView.as_view(), name='helpbot-unanswered-detail'),
    path('stats/', HelpbotStatsView.as_view(), name='helpbot-stats'),
    path('rebuild-index/', HelpbotRebuildIndexView.as_view(), name='helpbot-rebuild-index'),
]
