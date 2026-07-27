<?php

use Illuminate\Database\Migrations\Migration;

return new class extends Migration
{
    /**
     * Historically seeded two English GEO content prompts.
     *
     * Superseded by 2026_07_27_190000_replace_english_with_china_geo_content_prompts
     * (China-ecosystem Chinese templates). Kept as a no-op so migration history
     * remains stable for databases that already ran this file.
     */
    public function up(): void
    {
        // No-op: English defaults removed in favour of China GEO Chinese prompts.
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        // No-op: original English rows are no longer part of the default seed set.
    }
};
