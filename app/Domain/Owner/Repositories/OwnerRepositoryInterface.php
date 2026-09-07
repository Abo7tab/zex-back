<?php

namespace App\Domain\Owner\Repositories;

use App\Domain\Owner\Models\Owner;

interface OwnerRepositoryInterface
{
    public function create(array $attributes): Owner;
    public function findByEmail(string $email): ?Owner;
}
