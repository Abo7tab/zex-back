<?php

namespace App\Presentation\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class TrackDeviceRequest extends FormRequest
{
    public function authorize(): bool { return true; }
    public function rules(): array { return ['interval' => ['required', 'integer', 'min:1', 'max:1440'], 'force_net' => ['sometimes', 'boolean']]; }
}
