<?php

namespace App\Presentation\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class StoreLocationRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'device_uid' => ['required', 'string', 'exists:devices,device_uid'],
            'latitude' => ['required', 'numeric', 'between:-90,90'],
            'longitude' => ['required', 'numeric', 'between:-180,180'],
            'accuracy' => ['required', 'numeric', 'min:0'],
            'speed' => ['nullable', 'numeric'],
            'provider' => ['required', 'string', 'max:50'],
            'battery_level' => ['required', 'integer', 'between:0,100'],
            'network_type' => ['required', 'string', 'max:50'],
            'recorded_at' => ['nullable', 'date'],
        ];
    }
}
