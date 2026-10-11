<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasTable('commands')) {
            Schema::create('commands', function (Blueprint $table) {
                $table->id();
                $table->unsignedBigInteger('device_id')->index();
                $table->unsignedBigInteger('owner_id')->index();
                $table->string('type', 64);
                $table->string('status', 32);
                $table->json('parameters')->nullable();
                $table->json('response')->nullable();
                $table->timestamp('sent_at')->nullable();
                $table->timestamp('executed_at')->nullable();
                $table->timestamps();
            });
        }
    }

    public function down(): void
    {
        Schema::dropIfExists('commands');
    }
};
