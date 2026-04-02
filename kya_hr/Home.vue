<template>
	<BaseLayout>
		<template #body>
			<div class="flex flex-col items-center my-7 p-4 gap-7">
				<CheckInPanel />

				<KYALinks v-if="kyaLinks.length" :links="kyaLinks" :title="__('Flux RH KYA')" />

				<KYADocuments
					:documents="myDocuments"
					:total="myDocumentsTotal"
					:loading="loadingDocs"
					:title="__('Mes Demandes')"
				/>

				<KYASurveys
					:available="surveysAvailable"
					:completed="surveysCompleted"
					:tabs="surveysTabs"
					:counts="surveysCounts"
					:filters="surveysFilters"
					:loading="loadingSurveys"
					:title="__('Enquêtes & Évaluations')"
					@filter-change="onSurveyFilterChange"
				/>

				<KYATasks :tasks="myTasks" :plans="myPlans" :loading="loadingTasks" :title="__('Mes Tâches')" />

				<QuickLinks
					v-if="shouldShowLegacyQuickLinks && filteredQuickLinks.length"
					:items="filteredQuickLinks"
					:title="__('Quick Links')"
				/>

				<RequestPanel />
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { inject, markRaw, ref, computed, onMounted } from "vue"
import { frappeRequest } from "frappe-ui"

import CheckInPanel from "@/components/CheckInPanel.vue"
import QuickLinks from "@/components/QuickLinks.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import RequestPanel from "@/components/RequestPanel.vue"
import KYALinks from "@/components/KYALinks.vue"
import KYADocuments from "@/components/KYADocuments.vue"
import KYASurveys from "@/components/KYASurveys.vue"
import KYATasks from "@/components/KYATasks.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import ShiftIcon from "@/components/icons/ShiftIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import EmployeeAdvanceIcon from "@/components/icons/EmployeeAdvanceIcon.vue"
import SalaryIcon from "@/components/icons/SalaryIcon.vue"

const __ = inject("$translate")

const userCategory = ref("employee")
const surveyFilterParams = ref({})

const quickLinks = [
	{
		icon: markRaw(AttendanceIcon),
		title: __("Request Attendance"),
		route: "AttendanceRequestFormView",
	},
	{
		icon: markRaw(ShiftIcon),
		title: __("Request a Shift"),
		route: "ShiftRequestFormView",
	},
	{
		icon: markRaw(LeaveIcon),
		title: __("Request Leave"),
		route: "LeaveApplicationFormView",
		showFor: ["employee", "prestataire"],
	},
	{
		icon: markRaw(ExpenseIcon),
		title: __("Claim an Expense"),
		route: "ExpenseClaimFormView",
		showFor: ["employee"],
	},
	{
		icon: markRaw(EmployeeAdvanceIcon),
		title: __("Request an Advance"),
		route: "EmployeeAdvanceFormView",
		showFor: ["employee"],
	},
	{
		icon: markRaw(SalaryIcon),
		title: __("View Salary Slips"),
		route: "SalarySlipsDashboard",
		showFor: ["employee"],
	},
]

const filteredQuickLinks = computed(() => {
	const cat = userCategory.value
	return quickLinks.filter(
		(item) => !item.showFor || item.showFor.includes("all") || item.showFor.includes(cat)
	)
})

const shouldShowLegacyQuickLinks = computed(() => {
	return !["stage", "employee", "prestataire", "rh_manual"].includes(userCategory.value)
})

// Fallback links (used if API is unreachable) - mirrors get_kya_quick_links API
function fallbackKyaLinks(category) {
	const common = [
		{
			title: "PV Sortie Mat\u00e9riel",
			description: "D\u00e9clarer une sortie de mat\u00e9riel",
			url: "/pv-sortie-materiel",
			emoji: "\uD83D\uDCE6",
		},
		{
			title: "Demande d'Achat",
			description: "Soumettre une demande d'achat",
			url: "/demande-achat/new",
			emoji: "\uD83D\uDED2",
		},
	]

	if (category === "stage") {
		return [
			{
				title: "Permission de Sortie",
				description: "Demander une permission de sortie",
				url: "/permission-sortie-stagiaire/new",
				emoji: "\uD83D\uDEAA",
			},
			{
				title: "Bilan de Stage",
				description: "Remplir le bilan de fin de stage",
				url: "/bilan-fin-de-stage/new",
				emoji: "\uD83D\uDCDD",
			},
			...common,
		]
	}

	if (category === "rh_manual") {
		return [
			{
				title: "Permission Employ\u00e9 (RH)",
				description: "Saisie manuelle via Web Form",
				url: "/permission-sortie-employe/new",
				emoji: "\uD83E\uDDFE",
			},
			{
				title: "Permission Stagiaire (RH)",
				description: "Saisie manuelle via Web Form",
				url: "/permission-sortie-stagiaire/new",
				emoji: "\uD83C\uDF93",
			},
			{
				title: "Demande de Cong\u00e9 (RH)",
				description: "Saisie manuelle via Web Form",
				url: "/demande-conge/new",
				emoji: "\uD83D\uDCC5",
			},
			...common,
		]
	}

	// Default: employee / prestataire / CDI / CDD
	return [
		{
			title: "Permission de Sortie",
			description: "Demander une permission de sortie",
			url: "/permission-sortie-employe/new",
			emoji: "\uD83D\uDEAA",
		},
		{
			title: "Demande de Cong\u00e9",
			description: "Soumettre votre demande de cong\u00e9",
			url: "/demande-conge/new",
			emoji: "\uD83C\uDFD6\uFE0F",
		},
		{
			title: "Planning de Cong\u00e9",
			description: "G\u00e9rer vos p\u00e9riodes de cong\u00e9 annuelles",
			url: "/planning-conge/new",
			emoji: "\uD83D\uDCC5",
		},
		...common,
	]
}

// KYA custom links loaded from API
const kyaLinks = ref([])

// Document tracking
const myDocuments = ref([])
const myDocumentsTotal = ref(0)
const loadingDocs = ref(false)

// Enquêtes & Évaluations
const surveysAvailable = ref([])
const surveysCompleted = ref([])
const surveysTabs = ref({ actifs: [], en_attente: [], deja_repondu: [], fermes: [], historique: [] })
const surveysCounts = ref({ actifs: 0, en_attente: 0, deja_repondu: 0, fermes: 0, historique: 0 })
const surveysFilters = ref({ trimestres: ["T1", "T2", "T3", "T4"], annees: [], equipes: [], types: [] })
const loadingSurveys = ref(false)

// Tâches
const myTasks = ref([])
const myPlans = ref([])
const loadingTasks = ref(false)

async function loadSurveys(params = {}) {
	loadingSurveys.value = true
	try {
		const res = await frappeRequest({
			url: "/api/method/kya_hr.api.get_my_kya_forms",
			params,
		})
		if (res.message) {
			surveysAvailable.value = res.message.available || []
			surveysCompleted.value = res.message.completed || []
			surveysTabs.value = res.message.tabs || surveysTabs.value
			surveysCounts.value = res.message.counts || surveysCounts.value
			surveysFilters.value = res.message.filters || surveysFilters.value
		}
	} catch (e) {
		console.log("KYA surveys not available")
	} finally {
		loadingSurveys.value = false
	}
}

async function onSurveyFilterChange(filters) {
	surveyFilterParams.value = filters || {}
	await loadSurveys(surveyFilterParams.value)
}

onMounted(async () => {
	// 1. User category
	try {
		const catRes = await frappeRequest({
			url: "/api/method/kya_hr.api.get_user_category",
		})
		if (catRes.message) {
			userCategory.value = catRes.message.category || "employee"
		}
	} catch (e) {
		console.log("KYA user category not available, using employee fallback")
	}

	// 2. Quick links
	try {
		const res = await frappeRequest({
			url: "/api/method/kya_hr.api.get_kya_quick_links",
		})
		kyaLinks.value = (res.message && res.message.length) ? res.message : fallbackKyaLinks(userCategory.value)
	} catch (e) {
		kyaLinks.value = fallbackKyaLinks(userCategory.value)
		console.log("KYA links not available from API, fallback enabled")
	}

	// 3. Mes Demandes (documents)
	loadingDocs.value = true
	try {
		const res = await frappeRequest({
			url: "/api/method/kya_hr.api.get_my_documents",
			params: { limit: 10 },
		})
		if (res.message) {
			myDocuments.value = res.message.data || []
			myDocumentsTotal.value = res.message.total || 0
		}
	} catch (e) {
		console.log("KYA documents not available")
	}
	loadingDocs.value = false

	// 4. Enquêtes & Évaluations
	await loadSurveys(surveyFilterParams.value)

	// 5. Mes Tâches
	loadingTasks.value = true
	try {
		const res = await frappeRequest({
			url: "/api/method/kya_hr.api.get_my_tasks",
		})
		if (res.message) {
			myTasks.value = res.message.tasks || []
			myPlans.value = res.message.plans || []
		}
	} catch (e) {
		console.log("KYA tasks not available")
	}
	loadingTasks.value = false
})
</script>
