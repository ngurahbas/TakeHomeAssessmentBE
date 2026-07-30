<script lang="ts">
	import { page } from '$app/stores';
	import { Building2, CircleUser, LayoutDashboard } from 'lucide-svelte';
	import type { Snippet } from 'svelte';

	let { data, children }: { data: { user: { email: string; role: string } }; children: Snippet } =
		$props();

	const pathname = $derived($page.url.pathname);
	function isActive(prefix: string): boolean {
		return prefix === '/dashboard' ? pathname === '/dashboard' : pathname.startsWith(prefix);
	}

	const navItems = [
		{ href: '/dashboard', label: 'Overview', icon: LayoutDashboard, match: '/' },
		{ href: '/dashboard/properties', label: 'Properties', icon: Building2, match: '/properties' }
	] as const;
</script>

<div class="grid min-h-[calc(100vh-3.5rem)] grid-cols-1 md:grid-cols-[16rem_1fr]">
	<aside
		class="bg-surface-50-950 border-surface-200-800 hidden border-r md:flex md:flex-col"
	>
		<nav class="flex-1 space-y-1 p-4">
			<ul class="space-y-1">
				{#each navItems as item (item.href)}
					{@const active = isActive(item.match === '/' ? '/dashboard' : item.match)}
					<li>
						<a
							href={item.href}
							data-active={active}
							class="hover:preset-tonal-surface flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition data-[active]:preset-filled-primary-500 data-[active]:text-primary-contrast-500"
						>
							<item.icon size={18} strokeWidth={1.75} />
							<span>{item.label}</span>
						</a>
					</li>
				{/each}
			</ul>
		</nav>

		<div class="border-surface-200-800 border-t p-4">
			<div class="flex items-center gap-3">
				<span
					class="bg-primary-500/15 text-primary-500 grid h-9 w-9 shrink-0 place-items-center rounded-full"
				>
					<CircleUser size={18} strokeWidth={1.75} />
				</span>
				<div class="min-w-0 flex-1">
					<p class="truncate text-sm font-medium" title={data.user.email}>
						{data.user.email}
					</p>
					<span
						class={data.user.role === 'ADMIN'
							? 'badge preset-tonal-primary text-[10px]'
							: 'badge preset-tonal-surface text-[10px]'}
					>
						{data.user.role}
					</span>
				</div>
			</div>
		</div>
	</aside>

	<main class="min-w-0 p-4 sm:p-6">
		{@render children()}
	</main>
</div>
