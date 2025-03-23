from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
import json
from .models import SystemPrompt
from admin_panel.decorators import admin_required
from django.views.decorators.csrf import csrf_protect

@admin_required
def view_prompt(request):
    return render(request, 'prompt_management/prompt.html')

@admin_required
def get_prompts(request):
    prompts = list(SystemPrompt.objects.values('prompt_id', 'prompt_name', 'prompt_text', 'is_active'))
    return JsonResponse({'prompts': prompts})

@csrf_protect
def add_prompt(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            content = data.get('content', '').strip()
            is_active = data.get('isActive', True)

            if not name or not content:
                return JsonResponse({'error': 'Prompt Name and Content are required!'}, status=400)

            prompt = SystemPrompt.objects.create(
                prompt_name=name,
                prompt_text=content,
                is_active=is_active
            )

            return JsonResponse({'message': 'Prompt added successfully!', 'id': prompt.prompt_id}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data!'}, status=400)

    return JsonResponse({'error': 'Invalid request method!'}, status=405)

@csrf_protect
def edit_prompt(request, prompt_id):
    prompt = get_object_or_404(SystemPrompt, prompt_id=prompt_id)
    
    if request.method in ['POST', 'PUT']:  # Allow both PUT and POST
        try:
            data = json.loads(request.body)
            prompt.prompt_name = data.get('name', prompt.prompt_name)
            prompt.prompt_text = data.get('content', prompt.prompt_text)
            prompt.is_active = data.get('isActive', prompt.is_active)
            prompt.save()
            return JsonResponse({'message': 'Prompt updated successfully'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=405)

@csrf_protect
def delete_prompt(request, prompt_id):
    prompt = get_object_or_404(SystemPrompt, prompt_id=prompt_id)
    if request.method == 'DELETE':
        prompt.delete()
        return JsonResponse({'message': 'Prompt deleted successfully'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_protect
def toggle_status(request, prompt_id):
    prompt = get_object_or_404(SystemPrompt, prompt_id=prompt_id)
    if request.method == 'POST':
        prompt.is_active = not prompt.is_active
        prompt.save()
        return JsonResponse({'message': 'Status updated successfully'})
    return JsonResponse({'error': 'Invalid request'}, status=400)
