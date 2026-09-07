<?php

namespace App\Presentation\Http\Requests;

use App\Domain\Command\Enums\CommandStatus;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rules\Enum;

class CommandResponseRequest extends FormRequest
{
    public function authorize(): bool { return true; }
    public function rules(): array
    {
        return ['device_uid' => ['required', 'string'], 'status' => ['required', new Enum(CommandStatus::class)], 'response' => ['nullable', 'array']];
    }
}
