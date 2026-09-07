<?php

namespace App\Presentation\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class StopScreamRequest extends FormRequest
{
    public function authorize(): bool { return true; }
    public function rules(): array { return ['password' => ['required', 'string']]; }
}
