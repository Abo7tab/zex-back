<?php

namespace App\Infrastructure\Persistence\Eloquent;

use App\Domain\Owner\Models\Owner;
use App\Domain\Owner\Repositories\OwnerRepositoryInterface;

class EloquentOwnerRepository implements OwnerRepositoryInterface
{
    public function create(array $attributes): Owner { return Owner::create($attributes); }
    public function findByEmail(string $email): ?Owner { return Owner::where('email', $email)->first(); }
}
