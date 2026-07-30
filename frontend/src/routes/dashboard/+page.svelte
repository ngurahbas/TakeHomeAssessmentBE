<script lang="ts">
	import { Building2 } from 'lucide-svelte';

	let { data }: { data: { user: { email: string; role: string } } } = $props();
</script>

<svelte:head>
	<title>Dashboard · Real Estate AI</title>
</svelte:head>

<section class="mx-auto max-w-5xl space-y-6">
	<header class="space-y-1">
		<h1 class="h2">Dashboard</h1>
		<p class="opacity-70 text-sm">
			Signed in as <strong>{data.user.email}</strong> · {data.user.role}
		</p>
	</header>

	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
		<a
			href="/dashboard/properties"
			class="card preset-filled-surface-100-900 hover:preset-filled-surface-200-800 block p-5 transition"
		>
			<div class="flex items-center gap-3">
				<span
					class="bg-primary-500/15 text-primary-500 grid h-10 w-10 place-items-center rounded-full"
				>
					<Building2 size={18} strokeWidth={1.75} />
				</span>
				<h2 class="h4 leading-none">Properties</h2>
			</div>
			<p class="opacity-70 mt-3 text-sm">Browse, create, edit, and remove listings.</p>
		</a>
	</div>
</section>
