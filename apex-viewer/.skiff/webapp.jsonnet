/**
 * Kubernetes manifests for the static apex-viewer image: nginx serving the Vite
 * build (dist/) on port 8080. No Python, no database, no secrets — the design data
 * is baked into the image at build time from the committed all_workflows.zip (see
 * apex-viewer/Dockerfile). Resources are right-sized to 0.1 CPU / 256Mi.
 *
 * Two boilerplate files must sit alongside this one and are not authored here:
 * `.skiff/util.libsonnet` and `.skiff/cloudbuild-deploy.yaml`.
 */
local config = import '../skiff.json';
local util = import './util.libsonnet';

function(
    appImage, cause, sha, env='prod', branch='', repo='', buildId=''
)
    local domains = util.getHosts(env, config, '.apps.allenai.org') +
        util.getHosts(env, config, '.allen.ai') +
        if env == 'prod' && 'customDomains' in config then config.customDomains else [];

    local grouped = util.groupHosts(domains, ['.allenai.org', '.allen.ai', '.semanticscholar.org']);
    local canonical = grouped[0];
    local extra = grouped[1];
    local allenAIHosts = canonical['.allen.ai'];
    local hosts = canonical['.allenai.org'] + extra;

    local numReplicas = if env == 'prod' then config.replicas.prod else 1;
    local namespaceName = config.appName;
    local fullyQualifiedName = config.appName + '-' + env;

    local namespaceLabels = { app: config.appName, contact: config.contact, team: config.team };
    local labels = namespaceLabels + { env: env };
    local selectorLabels = { app: config.appName, env: env };
    local antiAffinityLabels = { onlyOneOfPerNode: config.appName + '-' + env };
    local podLabels = labels + antiAffinityLabels;
    local annotations = {
        'apps.allenai.org/sha': sha,
        'apps.allenai.org/branch': branch,
        'apps.allenai.org/repo': repo,
        'apps.allenai.org/build': buildId,
    };

    local proxyPort = 8080;       // service port exposed to the ingress proxy
    local appPort = 8080;         // nginx (static Vite build)
    local appHealthCheck = { port: appPort, scheme: 'HTTP' };

    local namespace = {
        apiVersion: 'v1',
        kind: 'Namespace',
        metadata: { name: namespaceName, labels: namespaceLabels },
    };

    local tls = util.getTLSConfig(fullyQualifiedName, hosts);
    local ingress = {
        apiVersion: 'networking.k8s.io/v1',
        kind: 'Ingress',
        metadata: {
            name: fullyQualifiedName,
            namespace: namespaceName,
            labels: labels,
            annotations: annotations + tls.ingressAnnotations + util.getAuthAnnotations(config, '.apps.allenai.org') + {
                'nginx.ingress.kubernetes.io/ssl-redirect': 'true',
            },
        },
        spec: {
            tls: [tls.spec + { hosts: hosts }],
            rules: [
                {
                    host: host,
                    http: { paths: [{
                        path: '/',
                        pathType: 'Prefix',
                        backend: { service: { name: fullyQualifiedName, port: { number: proxyPort } } },
                    }] },
                }
                for host in hosts
            ],
        },
    };

    local allenAITLS = util.getTLSConfig(fullyQualifiedName + '-allen-dot-ai', allenAIHosts);
    local allenAIIngress = {
        apiVersion: 'networking.k8s.io/v1',
        kind: 'Ingress',
        metadata: {
            name: fullyQualifiedName + '-allen-dot-ai',
            namespace: namespaceName,
            labels: labels,
            annotations: annotations + allenAITLS.ingressAnnotations + util.getAuthAnnotations(config, '.allen.ai') + {
                'nginx.ingress.kubernetes.io/ssl-redirect': 'true',
            },
        },
        spec: {
            tls: [allenAITLS.spec + { hosts: allenAIHosts }],
            rules: [
                {
                    host: host,
                    http: { paths: [{
                        path: '/',
                        pathType: 'Prefix',
                        backend: { service: { name: fullyQualifiedName, port: { number: proxyPort } } },
                    }] },
                }
                for host in allenAIHosts
            ],
        },
    };

    local deployment = {
        apiVersion: 'apps/v1',
        kind: 'Deployment',
        metadata: {
            labels: labels,
            name: fullyQualifiedName,
            namespace: namespaceName,
            annotations: annotations + { 'kubernetes.io/change-cause': cause },
        },
        spec: {
            strategy: { type: 'RollingUpdate', rollingUpdate: { maxSurge: numReplicas } },
            revisionHistoryLimit: 3,
            replicas: numReplicas,
            selector: { matchLabels: selectorLabels },
            template: {
                metadata: { name: fullyQualifiedName, namespace: namespaceName, labels: podLabels, annotations: annotations },
                spec: {
                    affinity: {
                        podAntiAffinity: {
                            requiredDuringSchedulingIgnoredDuringExecution: [{
                                labelSelector: {
                                    matchExpressions: [
                                        { key: labelName, operator: 'In', values: [antiAffinityLabels[labelName]] }
                                        for labelName in std.objectFields(antiAffinityLabels)
                                    ],
                                },
                                topologyKey: 'kubernetes.io/hostname',
                            }],
                        },
                    },
                    containers: [{
                        name: fullyQualifiedName,
                        image: appImage,
                        readinessProbe: {
                            httpGet: appHealthCheck + { path: '/' },
                            periodSeconds: 10,
                            failureThreshold: 3,
                        },
                        // Static nginx: tiny. The baked-in data is ~110 MB on disk but
                        // served as files, so the resident footprint stays small.
                        resources: { requests: { cpu: '100m', memory: '256Mi' }, limits: {} },
                        // No secrets, no env: the image serves a baked-in static build.
                    }],
                },
            },
        },
    };

    local service = {
        apiVersion: 'v1',
        kind: 'Service',
        metadata: { name: fullyQualifiedName, namespace: namespaceName, labels: labels, annotations: annotations },
        spec: {
            selector: selectorLabels,
            ports: [{ port: proxyPort, targetPort: appPort, name: 'http' }],
        },
    };

    local pdb = {
        apiVersion: 'policy/v1',
        kind: 'PodDisruptionBudget',
        metadata: { name: fullyQualifiedName, namespace: namespaceName, labels: labels },
        spec: {
            minAvailable: if numReplicas > 1 then 1 else 0,
            selector: { matchLabels: selectorLabels },
        },
    };

    [namespace, ingress, allenAIIngress, deployment, service, pdb]
