from django.conf import settings
from django.db import models


class HelpbotQueryLog(models.Model):
    """
    Audit log of questions submitted to the Helpbot.
    Stores metadata, scope determination, feedback ratings, and timestamps.
    Never stores customer details or API keys.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='helpbot_queries',
    )
    question = models.CharField(max_length=500)
    topic = models.CharField(max_length=100)
    confidence = models.FloatField(default=0.0)
    in_scope = models.BooleanField(default=True)
    provider = models.CharField(max_length=20, default='local')  # 'local' or 'anthropic'
    answer = models.TextField(blank=True, default='')
    response_time_ms = models.PositiveIntegerField(default=0)
    helpful = models.BooleanField(null=True, blank=True)
    feedback_comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['topic']),
            models.Index(fields=['in_scope']),
        ]
        verbose_name = 'Helpbot Query Log'
        verbose_name_plural = 'Helpbot Query Logs'

    def __str__(self) -> str:
        status_str = "Helpful" if self.helpful is True else ("Unhelpful" if self.helpful is False else "No rating")
        return f"[{self.topic}] {self.question[:40]} ({status_str})"


class HelpbotUnanswered(models.Model):
    """
    Tracks questions that could not be confidently answered by the Knowledge Base.
    Enables administrators to draft new articles directly from insights.
    """
    question = models.CharField(max_length=500)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='helpbot_unanswered',
    )
    topic_guess = models.CharField(max_length=100, blank=True, default='')
    confidence = models.FloatField(default=0.0)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['resolved']),
        ]
        verbose_name = 'Helpbot Unanswered Query'
        verbose_name_plural = 'Helpbot Unanswered Queries'

    def __str__(self) -> str:
        return f"[{self.topic_guess or 'Unknown'}] {self.question[:50]}"
