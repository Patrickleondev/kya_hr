<template>
	<div class="flex flex-col gap-4 my-4 w-full" v-if="hasContent || loading">
		<div class="text-lg font-medium text-gray-900">{{ title }}</div>

		<div v-if="loading" class="text-sm text-gray-500 text-center py-4">Chargement…</div>

		<div v-if="!loading" class="flex flex-wrap gap-2">
			<select v-model="filtersLocal.trimestre" class="border rounded px-2 py-1 text-xs text-gray-700 bg-white">
				<option value="">Trimestre</option>
				<option v-for="t in filterOptions.trimestres" :key="t" :value="t">{{ t }}</option>
			</select>
			<select v-model="filtersLocal.annee" class="border rounded px-2 py-1 text-xs text-gray-700 bg-white">
				<option value="">Année</option>
				<option v-for="y in filterOptions.annees" :key="y" :value="y">{{ y }}</option>
			</select>
			<select v-model="filtersLocal.equipe" class="border rounded px-2 py-1 text-xs text-gray-700 bg-white">
				<option value="">Equipe cible</option>
				<option v-for="eq in filterOptions.equipes" :key="eq" :value="eq">{{ eq }}</option>
			</select>
			<select v-model="filtersLocal.type" class="border rounded px-2 py-1 text-xs text-gray-700 bg-white">
				<option value="">Type</option>
				<option v-for="tp in filterOptions.types" :key="tp" :value="tp">{{ tp }}</option>
			</select>
			<button class="text-xs px-2 py-1 rounded bg-blue-600 text-white" @click="applyFilters">Filtrer</button>
		</div>

		<div v-if="!loading" class="flex gap-1 overflow-x-auto">
			<button
				v-for="tab in tabDefs"
				:key="tab.key"
				@click="currentTab = tab.key"
				class="px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap"
				:class="currentTab === tab.key ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'"
			>
				{{ tab.label }} ({{ counts[tab.key] || 0 }})
			</button>
		</div>

		<div v-if="visibleItems.length" class="flex flex-col bg-white rounded shadow-sm">
			<a
				v-for="(form, idx) in visibleItems"
				:key="form.form_name || form.name"
				:href="form.url || '#'
				"
				class="flex flex-row p-4 items-center justify-between no-underline"
				:class="idx !== visibleItems.length - 1 && 'border-b'"
			>
				<div class="flex flex-row items-center gap-3 grow min-w-0">
					<span class="h-8 w-8 flex items-center justify-center text-lg rounded-full bg-blue-100">📋</span>
					<div class="min-w-0">
						<div class="text-sm font-medium text-gray-800 truncate">{{ form.titre || form.form_title }}</div>
						<div class="text-xs text-gray-500 mt-0.5">
							{{ form.type_formulaire || form.type || 'Formulaire' }}
							<span v-if="form.trimestre || form.annee"> · {{ form.trimestre || '-' }} {{ form.annee || '' }}</span>
							<span v-if="form.equipe_cible"> · {{ form.equipe_cible }}</span>
							<span v-if="form.date_limite"> · Limite {{ formatDate(form.date_limite) }}</span>
						</div>
					</div>
				</div>
				<div class="flex items-center gap-2 shrink-0">
					<span class="text-[10px] font-medium px-1.5 py-0.5 rounded-full" :class="badgeClass(form.badge)">
						{{ form.badge || 'En attente' }}
					</span>
					<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-400" />
				</div>
			</a>
		</div>

		<div v-if="!loading && !visibleItems.length" class="text-sm text-gray-400 text-center py-3">
			Aucun formulaire pour cet onglet
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch } from "vue"
import { FeatherIcon } from "frappe-ui"

const props = defineProps({
	title: { type: String, default: "Enquêtes & Évaluations" },
	available: { type: Array, default: () => [] },
	completed: { type: Array, default: () => [] },
	tabs: {
		type: Object,
		default: () => ({ actifs: [], en_attente: [], deja_repondu: [], fermes: [], historique: [] }),
	},
	counts: {
		type: Object,
		default: () => ({ actifs: 0, en_attente: 0, deja_repondu: 0, fermes: 0, historique: 0 }),
	},
	filters: {
		type: Object,
		default: () => ({ trimestres: ["T1", "T2", "T3", "T4"], annees: [], equipes: [], types: [] }),
	},
	loading: { type: Boolean, default: false },
})

const emit = defineEmits(["filter-change"])

const currentTab = ref("actifs")
const tabDefs = [
	{ key: "actifs", label: "Actifs" },
	{ key: "en_attente", label: "En attente" },
	{ key: "deja_repondu", label: "Déjà répondu" },
	{ key: "fermes", label: "Fermés" },
	{ key: "historique", label: "Historique" },
]

const filtersLocal = ref({ trimestre: "", annee: "", equipe: "", type: "" })

const counts = computed(() => {
	if (props.counts && Object.keys(props.counts).length) return props.counts
	return {
		actifs: props.available.filter((x) => !x.completed).length,
		en_attente: props.available.filter((x) => !x.completed).length,
		deja_repondu: props.completed.length,
		fermes: 0,
		historique: props.available.length + props.completed.length,
	}
})

const normalizedTabs = computed(() => {
	if (props.tabs && Object.keys(props.tabs).length) return props.tabs
	return {
		actifs: props.available.filter((x) => !x.completed).map((x) => ({ ...x, badge: x.completed ? "Répondu" : "En attente" })),
		en_attente: props.available.filter((x) => !x.completed).map((x) => ({ ...x, badge: "En attente" })),
		deja_repondu: props.completed.map((x) => ({ ...x, badge: "Répondu" })),
		fermes: [],
		historique: [
			...props.available.map((x) => ({ ...x, badge: x.completed ? "Répondu" : "En attente" })),
			...props.completed.map((x) => ({ ...x, badge: "Répondu" })),
		],
	}
})

const filterOptions = computed(() => {
	if (props.filters && Object.keys(props.filters).length) return props.filters
	return { trimestres: ["T1", "T2", "T3", "T4"], annees: [], equipes: [], types: [] }
})

const visibleItems = computed(() => normalizedTabs.value[currentTab.value] || [])

watch(
	() => props.tabs,
	() => {
		if (!normalizedTabs.value[currentTab.value]) currentTab.value = "actifs"
	}
)

const hasContent = computed(() => {
	return tabDefs.some((t) => (normalizedTabs.value[t.key] || []).length > 0)
})

function applyFilters() {
	emit("filter-change", {
		trimestre: filtersLocal.value.trimestre || null,
		annee: filtersLocal.value.annee || null,
		equipe_cible: filtersLocal.value.equipe || null,
		type_formulaire: filtersLocal.value.type || null,
	})
}

function badgeClass(badge) {
	const b = (badge || "").toLowerCase()
	if (b.includes("répondu")) return "bg-green-100 text-green-700"
	if (b.includes("ferm")) return "bg-gray-100 text-gray-600"
	if (b.includes("retard")) return "bg-red-100 text-red-700"
	return "bg-orange-100 text-orange-700"
}

function formatDate(dateStr) {
	if (!dateStr) return ""
	const d = new Date(dateStr)
	return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" })
}
</script>
