<?php
namespace App\Presentation\Http\Requests;
use Illuminate\Foundation\Http\FormRequest;

class StoreAlertRequest extends FormRequest
{
    public function authorize(): bool { return true; }
    public function rules(): array
    {
        return [
            'type' => 'required|string|max:50',
            'message' => 'required|string|max:1000',
            'photo_url' => 'nullable|string|url',
            'latitude' => 'nullable|numeric',
            'longitude' => 'nullable|numeric',
        ];
    }
}
