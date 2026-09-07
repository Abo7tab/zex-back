<?php

namespace App\Presentation\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class HeartbeatRequest extends FormRequest
{
    public function authorize(): bool { return true; }
    public function rules(): array
    {
        return ['device_uid' => ['required', 'string', 'exists:devices,device_uid'], 'battery_level' => ['nullable', 'integer', 'between:0,100']];
    }
}
