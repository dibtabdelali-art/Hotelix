from pathlib import Path
import mimetypes
import os

from django.urls import path, include
from django.http import HttpResponse, FileResponse
from rest_framework.routers import DefaultRouter

from .views import ChatbotViewSet


BASE_DIR = Path(__file__).resolve().parent.parent


def _serve_template(filename: str):
	def _inner(request):
		path = BASE_DIR / 'frontend' / 'templates' / filename
		if not path.exists():
			return HttpResponse('Not found', status=404)
		return HttpResponse(path.read_text(encoding='utf-8'), content_type='text/html')
	return _inner


def _serve_static(request, filepath: str):
	path = BASE_DIR / 'frontend' / 'static' / filepath
	if not path.exists():
		return HttpResponse('Not found', status=404)
	content_type, _ = mimetypes.guess_type(str(path))
	return FileResponse(open(path, 'rb'), content_type=content_type or 'application/octet-stream')


router = DefaultRouter()
router.register(r'chatbot', ChatbotViewSet, basename='chatbot')

urlpatterns = [
	path('', _serve_template('chatbot.html'), name='home'),
	path('chatbot.html', _serve_template('chatbot.html'), name='home_html'),
	path('chat/', _serve_template('coversation.html'), name='chat'),
	path('coversation.html', _serve_template('coversation.html'), name='chat_html'),
	path('static/<path:filepath>', _serve_static, name='static'),
	path('api/', include(router.urls)),
]
