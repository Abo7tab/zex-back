<?php

namespace App\Application\Location\DTOs;

readonly class LocationDataDTO
{
    public function __construct(
        public float $latitude,
        public float $longitude,
        public ?float $accuracy = null,
        public ?float $speed = null,
        public ?string $recorded_at = null
    ) {}
}
