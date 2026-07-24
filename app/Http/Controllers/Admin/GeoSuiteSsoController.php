<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\Admin;
use App\Support\AdminActivityLogger;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Log;
use Throwable;

/**
 * GEO Suite SSO：校验 GEORank 签发的短时 ticket，建立 admin 会话。
 */
class GeoSuiteSsoController extends Controller
{
    public function consume(Request $request): RedirectResponse
    {
        $ticket = trim((string) $request->query('ticket', ''));
        if ($ticket === '' || ! str_contains($ticket, '.')) {
            return redirect()->route('admin.login')->withErrors([
                'username' => 'SSO ticket 无效或缺失',
            ]);
        }

        try {
            $payload = $this->verifyTicket($ticket);
        } catch (Throwable $exception) {
            Log::warning('geo_suite.sso_ticket_invalid', [
                'message' => $exception->getMessage(),
            ]);

            return redirect()->route('admin.login')->withErrors([
                'username' => 'SSO ticket 校验失败：'.$exception->getMessage(),
            ]);
        }

        $admin = $this->resolveAdmin($payload);
        if (! $admin instanceof Admin) {
            return redirect()->route('admin.login')->withErrors([
                'username' => '无法映射 GEORank 用户到 GEOFlow 管理员，请确认邮箱/用户名一致或配置 GEOSUITE_SSO_DEFAULT_ADMIN',
            ]);
        }

        Auth::guard('admin')->login($admin, true);
        $request->session()->regenerate();
        $admin->forceFill(['last_login' => now()])->save();
        AdminActivityLogger::logFromRequest($request, $admin, 'auth:sso_login', [
            'rank_user_id' => (string) ($payload['rank_user_id'] ?? ''),
            'email' => (string) ($payload['email'] ?? ''),
        ]);

        $next = (string) ($payload['next'] ?? '/geo_admin/dashboard');
        if (! str_starts_with($next, '/')) {
            $next = '/geo_admin/dashboard';
        }

        return redirect()->to($next);
    }

    /**
     * @return array<string, mixed>
     */
    private function verifyTicket(string $ticket): array
    {
        [$body, $sig] = explode('.', $ticket, 2);
        $secret = trim((string) env('GEOSUITE_SSO_SECRET', ''));
        if ($secret === '') {
            throw new \RuntimeException('GEOSUITE_SSO_SECRET 未配置');
        }

        $expected = hash_hmac('sha256', $body, $secret);
        if (! hash_equals($expected, $sig)) {
            throw new \RuntimeException('签名不匹配');
        }

        $pad = strlen($body) % 4;
        if ($pad > 0) {
            $body .= str_repeat('=', 4 - $pad);
        }
        $json = base64_decode(strtr($body, '-_', '+/'), true);
        if ($json === false) {
            throw new \RuntimeException('ticket 无法解码');
        }
        $payload = json_decode($json, true);
        if (! is_array($payload)) {
            throw new \RuntimeException('ticket payload 无效');
        }

        $exp = (int) ($payload['exp'] ?? 0);
        if ($exp < time()) {
            throw new \RuntimeException('ticket 已过期');
        }
        if (($payload['aud'] ?? '') !== 'geoflow' || ($payload['iss'] ?? '') !== 'georank') {
            throw new \RuntimeException('iss/aud 不匹配');
        }

        $nonce = (string) ($payload['nonce'] ?? '');
        if ($nonce === '') {
            throw new \RuntimeException('缺少 nonce');
        }
        $cacheKey = 'geosuite:sso:nonce:'.$nonce;
        if (! Cache::add($cacheKey, 1, 120)) {
            throw new \RuntimeException('ticket 已被使用');
        }

        return $payload;
    }

    /**
     * @param  array<string, mixed>  $payload
     */
    private function resolveAdmin(array $payload): ?Admin
    {
        $email = strtolower(trim((string) ($payload['email'] ?? '')));
        $username = trim((string) ($payload['username'] ?? ''));

        if ($email !== '') {
            $byEmail = Admin::query()->whereRaw('LOWER(email) = ?', [$email])->where('status', 'active')->first();
            if ($byEmail instanceof Admin) {
                return $byEmail;
            }
        }
        if ($username !== '') {
            $byName = Admin::query()->where('username', $username)->where('status', 'active')->first();
            if ($byName instanceof Admin) {
                return $byName;
            }
        }

        $fallback = trim((string) env('GEOSUITE_SSO_DEFAULT_ADMIN', 'admin'));
        if ($fallback === '') {
            return null;
        }

        $admin = Admin::query()->where('username', $fallback)->where('status', 'active')->first();

        return $admin instanceof Admin ? $admin : null;
    }
}
