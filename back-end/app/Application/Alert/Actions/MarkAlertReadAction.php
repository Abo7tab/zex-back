<?php

namespace App\Application\Alert\Actions;

use App\Domain\Alert\Models\Alert;
use App\Domain\Alert\Repositories\AlertRepositoryInterface;
use App\Domain\Owner\Models\Owner;
use Illuminate\Auth\Access\AuthorizationException;

class MarkAlertReadAction
{
    public function __construct(private AlertRepositoryInterface $alerts) {}
    public function execute(Owner $owner, Alert $alert): Alert
    {
        if ($alert->owner_id !== $owner->id) throw new AuthorizationException();
        $alert->update(['is_read' => true]);
        return $alert->refresh();
    }
}
