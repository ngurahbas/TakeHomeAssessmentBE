<script lang="ts">
	let { data } = $props();
</script>

<section class="space-y-4">
	<h1 class="h1">Welcome</h1>
	{#if data.user}
		<p class="opacity-80">
			Signed in as <strong>{data.user.email}</strong> ({data.user.role}).
		</p>
		<p class="opacity-60">More pages will land here soon.</p>
	{:else}
		<p class="opacity-80">You are not signed in.</p>
		<a href="/login" class="btn preset-filled-primary-500">Sign in</a>
	{/if}
</section>
