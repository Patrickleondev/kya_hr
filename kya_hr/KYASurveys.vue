<template>
	<div class="flex flex-col gap-4 my-4 w-full" v-if="hasContent || loading">
		<div class="text-lg font-medium text-gray-900">{{ title }}</div>

		<div v-if="loading" class="text-sm text-gray-500 text-center py-4">
			Chargement…
		</div>

		<!-- Enquêtes/Évaluations disponibles -->
		<div v-if="available.length" class="flex flex-col bg-white rounded shadow-sm">
			<a
				v-for="(form, idx) in available"
				:key="form.name"
				:href="form.url"
				class="flex flex-row p-4 items-center justify-between no-underline"
				:class="idx !== available.length - 1 && 'border-b'"
			>
				<div class="flex flex-row items-center gap-3 grow min-w-0">
					<span class="h-8 w-8 flex items-center justify-center text-lg rounded-full"
						:class="form.type === 'Évaluation' ? 'bg-purple-100' : 'bg-blue-100'">
						{{ form.type === 'Évaluation' ? '📊' : '📋' }}
					</span>
					<div class="min-w-0">
						<div class="text-sm font-medium text-gray-800 truncate">
							{{ form.titre }}
						</div>
						<div class="text-xs text-gray-500 mt-0.5">
							{{ form.type }}
							<span v-if="form.date_fin"> · Expire le {{ formatDate(form.date_fin) }}</span>
						</div>
					</div>
				</div>
				<div class="flex items-center gap-2 shrink-0">
					<span
						v-if="form.completed"
						class="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-green-100 text-green-700"
					>
						Répondu
					</span>
					<span
						v-else
						class="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-orange-100 text-orange-700"
					>
						À remplir
					</span>
					<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-400" />
				</div>
			</a>
		</div>

		<!-- Historique réponses -->
		<div v-if="completed.length && showHistory">
			<div class="text-sm font-medium text-gray-600 mb-2">Mes réponses</div>
			<div class="flex flex-col bg-white rounded shadow-sm">
				<div
					v-for="(resp, idx) in completed.slice(0, 5)"
					:key="resp.name"
					class="flex flex-row p-3 items-center gap-3"
					:class="idx !== Math.min(completed.length, 5) - 1 && 'border-b'"
				>
					<span class="text-green-500">✓</span>
					<div class="min-w-0 grow">
						<div class="text-sm text-gray-700 truncate">{{ resp.form_title }}</div>
						<div class="text-xs text-gray-400">{{ formatDate(resp.date) }}</div>
					</div>
				</div>
			</div>
		</div>

		<button
			v-if="completed.length && !showHistory"
			@click="showHistory = true"
			class="text-sm text-blue-600 font-medium text-center"
		>
			Voir mes {{ completed.length }} réponse(s)
		</button>

		<div
			v-if="!loading && !available.length && !completed.length"
			class="text-sm text-gray-400 text-center py-3"
		>
			Aucune enquête disponible
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from "vue"
import { FeatherIcon } from "frappe-ui"

const props = defineProps({
	title: { type: String, default: "Enquêtes & Évaluations" },
	available: { type: Array, default: () => [] },
	completed: { type: Array, default: () => [] },
	loading: { type: Boolean, default: false },
})

const showHistory = ref(false)

const hasContent = computed(() => {
	return props.available.length > 0 || props.completed.length > 0
})

function formatDate(dateStr) {
	if (!dateStr) return ""
	const d = new Date(dateStr)
	return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" })
}
</script>
