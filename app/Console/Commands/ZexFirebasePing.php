<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Kreait\Firebase\Contract\Database;
use Exception;

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
        } catch (Exception $e) {
            $this->error('Failed to ping Firebase: ' . $e->getMessage());
        }
    }
}
