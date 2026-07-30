<script lang="ts">
	import { ArrowRight, MessageSquareWarning } from 'lucide-svelte';
	import type { AiEscalationList } from './ai-escalations.types';

	let {
		data
	}: {
		data: { list: AiEscalationList; limit: number; offset: number };
	} = $props();

	const list = $derived(data.list);
	const limit = $derived(data.limit);
	const start = $derived(list.offset + 1);
	const end = $derived(list.offset + list.items.length);
	const totalPages = $derived(Math.max(1, Math.ceil(list.total / list.limit)));
	const currentPage = $derived(Math.floor(list.offset / list.limit) + 1);

	function buildHref(nextOffset: number): string {
		const qs = new URLSearchParams();
		qs.set('limit', String(limit));
		qs.set('offset', String(Math.max(0, nextOffset)));
		return `/dashboard/ai-escalations?${qs.toString()}`;
	}

	function formatDate(iso: string): string {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toISOString().slice(0, 10);
	}

	function formatDateTime(iso: string): string {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toISOString().replace('T', ' ').slice(0, 16);
	}

	function intentionPreview(text: string): string {
		const trimmed = text.trim();
		if (trimmed.length <= 80) return trimmed;
		return `${trimmed.slice(0, 77).trimEnd()}…`;
	}
</script>

<svelte:head>
	<title>AI Escalations · Real Estate AI</title>
</svelte:head>

<section class="space-y-6">
	<header class="flex flex-wrap items-end justify-between gap-3">
		<div>
			<h1 class="h2">AI Escalations</h1>
			<p class="opacity-70 text-sm">
				{list.total.toLocaleString()} total · showing {list.items.length === 0 ? 0 : start}–{end}
			</p>
		</div>
	</header>

	<div class="card preset-filled-surface-100-900 overflow-x-auto">
		{#if list.items.length === 0}
			<div class="space-y-2 p-10 text-center text-sm opacity-70">
				<MessageSquareWarning
					size={20}
					strokeWidth={1.75}
					class="mx-auto opacity-60"
				/>
				<p>No escalations yet.</p>
			</div>
		{:else}
			<table class="table">
				<thead>
					<tr>
						<th>ID</th>
						<th>Public chat</th>
						<th>User intention</th>
						<th class="text-right">Messages</th>
						<th>Created</th>
						<th class="text-right">Actions</th>
					</tr>
				</thead>
				<tbody>
					{#each list.items as e (e.id)}
						<tr>
							<td class="whitespace-nowrap">
								<a
									href={`/dashboard/ai-escalations/${e.id}`}
									class="anchor flex items-center gap-2 font-medium"
								>
									<span class="badge preset-tonal-warning text-[10px]">#{e.id}</span>
								</a>
							</td>
							<td class="whitespace-nowrap font-mono text-xs opacity-80" title={e.public_chat_id}>
								{e.public_chat_id}
							</td>
							<td class="max-w-[28rem]">
								<span class="line-clamp-1" title={e.user_intention}>
									{intentionPreview(e.user_intention)}
								</span>
							</td>
							<td class="text-right tabular-nums">{e.message_count}</td>
							<td class="whitespace-nowrap text-xs opacity-70" title={formatDateTime(e.created_at)}>
								{formatDate(e.created_at)}
							</td>
							<td>
								<div class="flex items-center justify-end gap-1">
									<a
										href={`/dashboard/ai-escalations/${e.id}`}
										class="btn btn-sm preset-tonal-surface"
									>
										<ArrowRight size={14} strokeWidth={1.75} />
										<span>View</span>
									</a>
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>

	{#if list.total > list.limit}
		<nav class="flex items-center justify-between text-sm" aria-label="Pagination">
			<p class="opacity-70">
				Page {currentPage} of {totalPages}
			</p>
			<div class="flex items-center gap-2">
				<a
					class="btn btn-sm preset-tonal-surface"
					class:opacity-50={currentPage <= 1}
					aria-disabled={currentPage <= 1}
					href={buildHref(list.offset - list.limit)}
				>
					Previous
				</a>
				<a
					class="btn btn-sm preset-tonal-surface"
					class:opacity-50={currentPage >= totalPages}
					aria-disabled={currentPage >= totalPages}
					href={buildHref(list.offset + list.limit)}
				>
					Next
				</a>
			</div>
		</nav>
	{/if}
</section>
