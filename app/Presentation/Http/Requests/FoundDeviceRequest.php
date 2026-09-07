<?php

namespace App\Presentation\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class FoundDeviceRequest extends FormRequest
{
    public function authorize(): bool { return true; }
    public function rules(): array { return ['pin_code' => ['required', 'digits:6']]; }
}
