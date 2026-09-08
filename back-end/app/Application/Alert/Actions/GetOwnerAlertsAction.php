<?php

namespace App\Application\Alert\Actions;

use App\Domain\Alert\Repositories\AlertRepositoryInterface;
use App\Domain\Owner\Models\Owner;

class GetOwnerAlertsAction
{
    public function __construct(private AlertRepositoryInterface $alerts) {}
    public function execute(Owner $owner): array { return [$this->alerts->forOwner($owner), $this->alerts->unreadCount($owner)]; }
}
