<?php

namespace App\Presentation\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class StoreAlertRequest extends FormRequest
{
    public function authorize(): bool { return true; }
    public function rules(): array { return ['device_uid' => ['required', 'string'], 'type' => ['required', Rule::in(['SIM_CHANGED', 'WRONG_PASS', 'SHUTDOWN', 'RESET', 'UNINSTALL'])], 'message' => ['required', 'string', 'max:2000']]; }
}
