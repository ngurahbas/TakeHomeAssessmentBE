<script lang="ts">
	import { Dialog } from '@skeletonlabs/skeleton-svelte';
	import { Trash2 } from 'lucide-svelte';
	import type { RemoteForm } from '@sveltejs/kit';
	import type * as v from 'valibot';
	import { PropertyIdSchema } from '../properties.schemas';

	type DeleteFormBase = RemoteForm<v.InferInput<typeof PropertyIdSchema>, unknown>;
	type DeleteFormInstance = Omit<DeleteFormBase, 'for'>;

	let {
		id,
		title,
		form,
		triggerLabel = 'Delete'
	}: {
		id: number;
		title: string;
		form: DeleteFormInstance;
		triggerLabel?: string;
	} = $props();

	let open = $state(false);

	const topLevelIssues = $derived(
		(() => {
			const issues = form.fields.issues();
			return (issues ?? []).filter((iss) => !iss.path || iss.path.length === 0);
		})()
	);
</script>

<Dialog open={open} onOpenChange={(e) => (open = e.open)}>
	<Dialog.Trigger class="btn btn-sm preset-tonal-error">
		<Trash2 size={14} strokeWidth={1.75} />
		<span>{triggerLabel}</span>
	</Dialog.Trigger>
	<Dialog.Backdrop class="fixed inset-0 z-50 bg-surface-950/50 backdrop-blur-sm" />
	<Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-4">
		<Dialog.Content
			class="card preset-filled-surface-100-900 w-full max-w-md space-y-4 p-6 shadow-xl"
		>
			<Dialog.Title class="h3">Delete this property?</Dialog.Title>
			<Dialog.Description class="text-sm opacity-70">
				This will permanently remove <strong>{title}</strong>. This action cannot be undone.
			</Dialog.Description>

			{#if topLevelIssues.length > 0}
				<div role="alert" class="alert preset-tonal-error p-3 text-sm">
					{#each topLevelIssues as issue (issue)}
						<span>{issue.message}</span>
					{/each}
				</div>
			{/if}

			<form
				{...form}
				method="POST"
				class="flex items-center justify-end gap-2"
				onsubmit={() => (open = false)}
			>
				<input type="hidden" name="id" value={id} />
				<Dialog.CloseTrigger class="btn preset-tonal-surface">Cancel</Dialog.CloseTrigger>
				<button type="submit" class="btn preset-filled-error-500" disabled={!!form.pending}>
					<Trash2 size={14} strokeWidth={1.75} />
					<span>Delete</span>
				</button>
			</form>
		</Dialog.Content>
	</Dialog.Positioner>
</Dialog>
