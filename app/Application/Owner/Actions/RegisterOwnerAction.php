<?php

namespace App\Application\Owner\Actions;

use App\Domain\Owner\Models\Owner;
use App\Domain\Owner\Repositories\OwnerRepositoryInterface;

class RegisterOwnerAction
{
    public function __construct(private OwnerRepositoryInterface $owners) {}

    public function execute(array $data): array
    {
        $owner = $this->owners->create($data);
        return [$owner, $owner->createToken('owner-api')->plainTextToken];
    }
}
