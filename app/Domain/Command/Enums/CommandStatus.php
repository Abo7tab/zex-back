<?php

namespace App\Domain\Command\Enums;

enum CommandStatus: string
{
    case PENDING = 'PENDING';
    case SENT = 'SENT';
    case EXECUTED = 'EXECUTED';
    case FAILED = 'FAILED';
}
