<script lang="ts">
	import { login } from './auth.remote';

	const passwordIssues = $derived(login.fields.password.issues() ?? []);
</script>

<section class="mx-auto max-w-md space-y-6">
	<header class="space-y-1">
		<h1 class="h2">Sign in</h1>
		<p class="opacity-70 text-sm">Use your administrator account to continue.</p>
	</header>

	<form {...login} class="card preset-filled-surface-100-900 space-y-4 p-6">
		<label class="label">
			<span class="label-text">Email</span>
			<input
				{...login.fields.email.as('email')}
				class="input"
				autocomplete="email"
				required
			/>
		</label>

		<label class="label">
			<span class="label-text">Password</span>
			<input
				{...login.fields.password.as('password')}
				class="input"
				autocomplete="current-password"
				required
			/>
			{#if passwordIssues.length > 0}
				{#each passwordIssues as issue (issue)}
					<small class="text-error-500">{issue.message}</small>
				{/each}
			{/if}
		</label>

		<button class="btn preset-filled-primary-500 w-full" type="submit">Sign in</button>
	</form>
</section>
