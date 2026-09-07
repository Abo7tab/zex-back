<?php

namespace App\Application\Owner\Actions;

use App\Domain\Owner\Repositories\OwnerRepositoryInterface;
use Illuminate\Auth\AuthenticationException;
use Illuminate\Support\Facades\Hash;

class LoginOwnerAction
{
    public function __construct(private OwnerRepositoryInterface $owners) {}

    public function execute(string $email, string $password): array
    {
        $owner = $this->owners->findByEmail($email);
        if (! $owner || ! Hash::check($password, $owner->password)) {
            throw new AuthenticationException('Invalid credentials');
        }
        return [$owner, $owner->createToken('owner-api')->plainTextToken];
    }
}
