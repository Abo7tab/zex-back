<?php

namespace App\Providers;

use App\Domain\Alert\Repositories\AlertRepositoryInterface;
use App\Domain\Command\Repositories\CommandRepositoryInterface;
use App\Domain\Device\Repositories\DeviceRepositoryInterface;
use App\Domain\Location\Repositories\LocationRepositoryInterface;
use App\Domain\Owner\Repositories\OwnerRepositoryInterface;
use App\Infrastructure\Persistence\Eloquent\EloquentAlertRepository;
use App\Infrastructure\Persistence\Eloquent\EloquentCommandRepository;
use App\Infrastructure\Persistence\Eloquent\EloquentDeviceRepository;
use App\Infrastructure\Persistence\Eloquent\EloquentLocationRepository;
use App\Infrastructure\Persistence\Eloquent\EloquentOwnerRepository;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->bind(OwnerRepositoryInterface::class, EloquentOwnerRepository::class);
        $this->app->bind(DeviceRepositoryInterface::class, EloquentDeviceRepository::class);
        $this->app->bind(CommandRepositoryInterface::class, EloquentCommandRepository::class);
        $this->app->bind(LocationRepositoryInterface::class, EloquentLocationRepository::class);
        $this->app->bind(AlertRepositoryInterface::class, EloquentAlertRepository::class);
    }
}
