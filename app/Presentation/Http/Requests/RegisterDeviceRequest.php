<?php

namespace App\Presentation\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class RegisterDeviceRequest extends FormRequest
{
    public function authorize(): bool { return true; }

    protected function prepareForValidation(): void
    {
        $this->merge(['device_name' => $this->input('device_name', $this->input('name'))]);
    }

    public function rules(): array
    {
        return [
            'device_uid' => ['required', 'string', 'max:255', 'unique:devices,device_uid'],
            'device_name' => ['required', 'string', 'max:255'],
            'model' => ['nullable', 'string', 'max:255'],
            'os_version' => ['nullable', 'string', 'max:255'],
        ];
    }
}
