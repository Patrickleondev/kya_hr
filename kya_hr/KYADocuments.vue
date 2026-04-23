<template>
	<div class="flex flex-col gap-4 my-4 w-full" v-if="documents.length || loading">
		<div class="flex items-center justify-between">
			<div class="text-lg font-medium text-gray-900">{{ title }}</div>
			<button
				v-if="documents.length > 3 && !showAll"
				@click="showAll = true"
				class="text-sm text-blue-600 font-medium"
			>
				Voir tout ({{ total }})
			</button>
		</div>

		<div v-if="loading" class="text-sm text-gray-500 text-center py-4">
			Chargement…
		</div>

		<div v-else class="flex flex-col bg-white rounded shadow-sm">
			<a
				v-for="(doc, idx) in visibleDocs"
				:key="doc.name"
				:href="doc.url"
				class="flex flex-row p-4 items-center justify-between no-underline"
				:class="idx !== visibleDocs.length - 1 && 'border-b'"
			>
				<div class="flex flex-col gap-1 grow min-w-0">
					<div class="flex items-center gap-2">
						<span class="text-sm font-medium text-gray-800 truncate">
							{{ doc.label }}
						</span>
						<span
							class="text-[10px] font-medium px-1.5 py-0.5 rounded-full whitespace-nowrap"
							:class="badgeClass(doc.color)"
						>
							{{ doc.workflow_state }}
						</span>
					</div>
					<div class="text-xs text-gray-500">
						{{ doc.name }} · {{ formatDate(doc.modified) }}
					</div>
				</div>
				<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-400 shrink-0" />
			</a>
		</div>

		<div
			v-if="!loading && documents.length === 0"
			class="text-sm text-gray-400 text-center py-3"
		>
			Aucune demande en cours
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from "vue"
import { FeatherIcon } from "frappe-ui"

const props = defineProps({
	title: { type: String, default: "Mes Demandes" },
	documents: { type: Array, default: () => [] },
	total: { type: Number, default: 0 },
	loading: { type: Boolean, default: false },
})

const showAll = ref(false)

const visibleDocs = computed(() => {
	return showAll.value ? props.documents : props.documents.slice(0, 5)
})

function badgeClass(color) {
	const map = {
		green: "bg-green-100 text-green-700",
		red: "bg-red-100 text-red-700",
		blue: "bg-blue-100 text-blue-700",
		orange: "bg-orange-100 text-orange-700",
		yellow: "bg-yellow-100 text-yellow-700",
		gray: "bg-gray-100 text-gray-600",
	}
	return map[color] || map.gray
}

function formatDate(dateStr) {
	if (!dateStr) return ""
	const d = new Date(dateStr)
	return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" })
}
</script>
