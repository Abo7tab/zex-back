<?php

namespace App\Domain\Command\Enums;

enum CommandType: string
{
    case LOCATE = 'LOCATE';
    case CONTINUOUS_TRACK = 'CONTINUOUS_TRACK';
    case STOP_TRACKING = 'STOP_TRACKING';
    case SCREAM = 'SCREAM';
    case STOP_SCREAM = 'STOP_SCREAM';
    case LOCK = 'LOCK';
    case PHOTO = 'PHOTO';
    case ENABLE_NET = 'ENABLE_NET';
    case STOLEN_MODE = 'STOLEN_MODE';
    case FOUND_MODE = 'FOUND_MODE';
}
