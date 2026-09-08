<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Kreait\Firebase\Contract\Database;
use Throwable;

class ZexFirebasePing extends Command
{
    protected $signature = 'zex:firebase-ping';
    protected $description = 'Ping Firebase Realtime Database';

    public function handle(Database $database)
    {
        $this->info('Pinging Firebase Realtime Database...');
        
        try {
            $ref = $database->getReference('system/ping');
            $ref->set(['timestamp' => now()->toIso8601String()]);
            
            $value = $ref->getValue();
            $this->info('Success! Firebase responded with:');
            $this->line(json_encode($value, JSON_PRETTY_PRINT));
            return 0;
        } catch (Throwable $e) {
            $this->error('Failed to ping Firebase: ' . $e->getMessage());
            $this->warn('If curl -4 works, ensure CURLOPT_IPRESOLVE_V4 is applied.');
            return 1;
        }
    }
}
