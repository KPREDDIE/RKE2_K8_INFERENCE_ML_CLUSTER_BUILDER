{{- define "llm.engine" -}}{{ index .Values.engines .Values.engine | toYaml }}{{- end -}}
{{- define "llm.name" -}}{{ .Release.Name }}-{{ .Values.engine }}{{- end -}}
