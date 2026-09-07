<?php

namespace App\Presentation\Http\Requests;

use App\Domain\Command\Enums\CommandType;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rules\Enum;

class SendCommandRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'device_id' => ['required', 'integer', 'exists:devices,id'],
            'type' => ['required', new Enum(CommandType::class)],
            'parameters' => ['nullable', 'array'],
        ];
    }
}
