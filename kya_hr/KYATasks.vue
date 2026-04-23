<template>
	<div class="flex flex-col gap-4 my-4 w-full" v-if="hasContent || loading">
		<div class="text-lg font-medium text-gray-900">{{ title }}</div>

		<div v-if="loading" class="text-sm text-gray-500 text-center py-4">
			Chargement…
		</div>

		<!-- Tâches assignées -->
		<div v-if="tasks.length" class="flex flex-col bg-white rounded shadow-sm">
			<a
				v-for="(task, idx) in visibleTasks"
				:key="task.name"
				:href="task.url"
				class="flex flex-row p-4 items-start gap-3 no-underline"
				:class="idx !== visibleTasks.length - 1 && 'border-b'"
			>
				<span
					class="h-8 w-8 flex items-center justify-center text-xs font-bold rounded-full shrink-0 mt-0.5"
					:class="priorityClass(task.priorite)"
				>
					{{ priorityIcon(task.priorite) }}
				</span>
				<div class="grow min-w-0">
					<div class="text-sm font-medium text-gray-800 truncate">
						{{ task.titre }}
					</div>
					<div class="flex items-center gap-2 mt-1">
						<span
							class="text-[10px] font-medium px-1.5 py-0.5 rounded-full"
							:class="statusClass(task.statut)"
						>
							{{ task.statut }}
						</span>
						<span v-if="task.date_echeance" class="text-xs text-gray-400">
							{{ formatDate(task.date_echeance) }}
						</span>
					</div>
					<!-- Progress bar -->
					<div v-if="task.progression > 0" class="mt-2 w-full bg-gray-100 rounded-full h-1.5">
						<div
							class="h-1.5 rounded-full transition-all"
							:class="task.progression >= 100 ? 'bg-green-500' : 'bg-blue-500'"
							:style="{ width: Math.min(task.progression, 100) + '%' }"
						></div>
					</div>
				</div>
				<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-400 shrink-0 mt-1" />
			</a>
		</div>

		<!-- Plans trimestriels (Chef d'équipe) -->
		<div v-if="plans.length">
			<div class="text-sm font-medium text-gray-600 mb-2">Mes Plans d'Équipe</div>
			<div class="flex flex-col bg-white rounded shadow-sm">
				<a
					v-for="(plan, idx) in plans"
					:key="plan.name"
					:href="plan.url"
					class="flex flex-row p-4 items-center justify-between no-underline"
					:class="idx !== plans.length - 1 && 'border-b'"
				>
					<div class="min-w-0 grow">
						<div class="text-sm font-medium text-gray-800 truncate">
							{{ plan.titre }}
						</div>
						<div class="flex items-center gap-2 mt-1">
							<span class="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700">
								{{ plan.statut }}
							</span>
							<span v-if="plan.equipe" class="text-xs text-gray-400">
								{{ plan.equipe }}
							</span>
						</div>
						<div v-if="plan.progression > 0" class="mt-2 w-full bg-gray-100 rounded-full h-1.5">
							<div
								class="h-1.5 rounded-full bg-blue-500"
								:style="{ width: Math.min(plan.progression, 100) + '%' }"
							></div>
						</div>
					</div>
					<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-400 shrink-0" />
				</a>
			</div>
		</div>

		<div
			v-if="!loading && !tasks.length && !plans.length"
			class="text-sm text-gray-400 text-center py-3"
		>
			Aucune tâche assignée
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from "vue"
import { FeatherIcon } from "frappe-ui"

const props = defineProps({
	title: { type: String, default: "Mes Tâches" },
	tasks: { type: Array, default: () => [] },
	plans: { type: Array, default: () => [] },
	loading: { type: Boolean, default: false },
})

const showAll = ref(false)

const hasContent = computed(() => {
	return props.tasks.length > 0 || props.plans.length > 0
})

const visibleTasks = computed(() => {
	return showAll.value ? props.tasks : props.tasks.slice(0, 5)
})

function priorityClass(p) {
	const map = {
		"Critique": "bg-red-100 text-red-700",
		"Haute": "bg-orange-100 text-orange-700",
		"Moyenne": "bg-blue-100 text-blue-700",
		"Basse": "bg-gray-100 text-gray-600",
	}
	return map[p] || map["Moyenne"]
}

function priorityIcon(p) {
	const map = { "Critique": "!!", "Haute": "!", "Moyenne": "●", "Basse": "○" }
	return map[p] || "●"
}

function statusClass(s) {
	const map = {
		"Non démarré": "bg-gray-100 text-gray-600",
		"En cours": "bg-blue-100 text-blue-700",
		"En retard": "bg-red-100 text-red-700",
		"Terminé": "bg-green-100 text-green-700",
		"Annulé": "bg-gray-100 text-gray-500",
	}
	return map[s] || map["Non démarré"]
}

function formatDate(dateStr) {
	if (!dateStr) return ""
	const d = new Date(dateStr)
	return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" })
}
</script>
