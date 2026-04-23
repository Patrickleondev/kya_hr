<template>
	<div class="flex flex-col gap-5 my-4 w-full" v-if="links.length">
		<div class="text-lg font-medium text-gray-900">{{ title }}</div>
		<div class="flex flex-col bg-white rounded">
			<a
				v-for="(link, idx) in links"
				:key="link.title"
				:href="link.url"
				class="flex flex-row flex-start p-4 items-center justify-between no-underline"
				:class="idx !== links.length - 1 && 'border-b'"
			>
				<div class="flex flex-row items-center gap-3 grow">
					<span class="h-5 w-5 flex items-center justify-center text-base">{{
						link.emoji || "📋"
					}}</span>
					<div>
						<div class="text-base font-normal text-gray-800">
							{{ link.title }}
						</div>
						<div
							v-if="link.description"
							class="text-xs text-gray-500 mt-0.5"
						>
							{{ link.description }}
						</div>
					</div>
				</div>
				<FeatherIcon name="chevron-right" class="h-5 w-5 text-gray-500" />
			</a>
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui"

defineProps({
	title: {
		type: String,
		default: "Services KYA",
	},
	links: {
		type: Array,
		required: true,
	},
})
</script>
