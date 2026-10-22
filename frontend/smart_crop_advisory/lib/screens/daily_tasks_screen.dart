import 'package:flutter/material.dart';

import '../models/crop_cycle.dart';
import '../models/daily_task.dart';
import '../services/api_client.dart';
import '../services/auth_controller.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';

class DailyTasksScreen extends StatefulWidget {
  final AuthController auth;

  const DailyTasksScreen({super.key, required this.auth});

  @override
  State<DailyTasksScreen> createState() => _DailyTasksScreenState();
}

class _DailyTasksScreenState extends State<DailyTasksScreen> {
  DateTime _targetDate = DateTime.now();
  late Future<List<DailyTask>> _tasks;
  late Future<List<Map<String, dynamic>>> _weatherRisks;
  bool _generating = false;
  String? _error;
  String? _result;
  // Track which task IDs are being toggled (to show per-task spinner)
  final Set<int> _toggling = {};
  final Map<String, Map<String, bool>> _riskAnswers = {};
  final Set<String> _savingAssessments = {};
  final Set<String> _savedAssessments = {};

  List<String> _questionsForRisk(String riskName) {
    final name = riskName.toLowerCase();

    if (name.contains('leaf curl')) {
      return [
        'Are the leaves curling?',
        'Do the plants look stunted?',
        'Can you see whiteflies on the plants?',
      ];
    }

    if (name.contains('spotted wilt') || name.contains('bud necrosis')) {
      return [
        'Are buds or flowers damaged?',
        'Can you see ringspots or dead-looking patches?',
        'Can you see thrips on the plants?',
      ];
    }

    return [
      'Can you see the symptoms described in this alert?',
      'Are affected plants looking different from healthy plants?',
      'Is the problem appearing on more than one plant?',
    ];
  }

  String _guidanceForAnswers(Map<String, bool> answers, String prevention) {
    if (answers.values.any((answer) => answer)) {
      return 'One or more symptoms were reported. Inspect affected plants '
          'carefully and seek verified local agricultural guidance. '
          'Do not treat this assessment as a confirmed diagnosis. '
          'Knowledge-base guidance: $prevention';
    }

    return 'No listed symptoms were reported. Continue monitoring the crop, '
        'inspect plants regularly, and repeat the assessment if symptoms appear.';
  }

  Future<void> _saveRiskAssessment({
    required String key,
    required int cropCycleId,
    required String crop,
    required String riskName,
    required Map<String, bool> answers,
    required String guidance,
    required String details,
  }) async {
    if (_savingAssessments.contains(key) || _savedAssessments.contains(key)) {
      return;
    }

    setState(() => _savingAssessments.add(key));

    try {
      final note = [
        'Weather-risk assessment',
        'Date: ${_dateString(_targetDate)}',
        'Crop: $crop',
        'Alert: $riskName',
        '',
        'Symptom answers:',
        ...answers.entries.map(
          (entry) => '${entry.key}: ${entry.value ? 'Yes' : 'No'}',
        ),
        '',
        'Guidance shown:',
        guidance,
        '',
        'Weather-risk details:',
        details,
        '',
        'This is a preliminary assessment, not a confirmed diagnosis.',
      ].join('\n');

      await widget.auth.saveObservation(cropCycleId: cropCycleId, note: note);

      if (!mounted) return;

      setState(() => _savedAssessments.add(key));

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Assessment saved to Activity History.')),
      );
    } catch (error) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            error is ApiException
                ? error.message
                : 'Could not save the assessment. Please try again.',
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _savingAssessments.remove(key));
      }
    }
  }

  String _riskField(Map<String, dynamic> risk, List<String> possibleKeys) {
    for (final key in possibleKeys) {
      final value = risk[key]?.toString().trim();

      if (value != null &&
          value.isNotEmpty &&
          value.toLowerCase() != 'null' &&
          value.toLowerCase() != 'none') {
        return value;
      }
    }

    return '';
  }

  Widget _riskInfo(String label, String value) {
    if (value.trim().isEmpty) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpace.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: AppText.label),
          const SizedBox(height: 4),
          Text(value, style: AppText.body),
        ],
      ),
    );
  }

  Future<void> _showDiseaseTreatment({
    required String crop,
    required String disease,
  }) async {
    try {
      final details = await widget.auth.loadDiseaseTreatment(
        crop: crop,
        disease: disease,
      );
      if (!mounted) return;

      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: Text(
            '${details['disease'] ?? disease} — Treatment Information',
          ),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                _riskInfo('Marathi name', '${details['marathi_name'] ?? ''}'),
                _riskInfo('Chemical name', '${details['chemical_name'] ?? ''}'),
                _riskInfo('Combination', '${details['combination'] ?? ''}'),
                _riskInfo('Brand name', '${details['brand_name'] ?? ''}'),
                _riskInfo(
                  'Dosage and application instructions',
                  '${details['dosage_instructions'] ?? ''}',
                ),
                _riskInfo('Water pH', '${details['water_ph'] ?? ''}'),
                _riskInfo(
                  'Weather conditions',
                  '${details['weather_conditions'] ?? ''}',
                ),
                _riskInfo(
                  'Pre-harvest interval',
                  '${details['pre_harvest_interval'] ?? ''}',
                ),
                const SizedBox(height: AppSpace.md),
                const Text(
                  'Workbook treatment details need local verification. '
                  'Symptoms alone do not confirm a disease. Check the '
                  'product label and consult a qualified agricultural expert.',
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    } catch (error) {
      if (!mounted) return;
      final message = error is ApiException
          ? error.message
          : 'Could not load treatment details.';
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
    }
  }

  @override
  void initState() {
    super.initState();
    _tasks = widget.auth.loadTasks(_targetDate);
    _weatherRisks = _loadWeatherRisks(_targetDate);
  }

  bool _temperatureRuleMatches(Map<String, dynamic> risk) {
    final temperature = double.tryParse('${risk['temperature_c'] ?? ''}');
    if (temperature == null) return false;

    final operator = '${risk['temperature_operator'] ?? ''}'
        .trim()
        .toLowerCase();
    final minTemp = double.tryParse('${risk['temperature_min_c'] ?? ''}');
    final maxTemp = double.tryParse('${risk['temperature_max_c'] ?? ''}');

    switch (operator) {
      case 'between_inclusive':
        return minTemp != null &&
            maxTemp != null &&
            temperature >= minTemp &&
            temperature <= maxTemp;
      case 'greater_than':
        return minTemp != null && temperature > minTemp;
      case 'greater_than_or_equal':
      case 'at_least':
        return minTemp != null && temperature >= minTemp;
      case 'less_than':
        return maxTemp != null && temperature < maxTemp;
      default:
        return false;
    }
  }

  Future<List<Map<String, dynamic>>> _loadWeatherRisks(DateTime day) async {
    final cycles = await widget.auth.loadCropCycles();
    final results = <Map<String, dynamic>>[];
    final errors = <String>[];

    for (final CropCycle cycle in cycles) {
      try {
        final response = await widget.auth.loadWeatherRisk(cycle.id, day);
        final advisories = response['advisories'];
        final risks = advisories is Map ? advisories['risk_candidates'] : null;

        if (risks is List) {
          for (final item in risks) {
            if (item is! Map) continue;

            final risk = Map<String, dynamic>.from(item);
            if (!_temperatureRuleMatches(risk)) continue;

            results.add({
              'crop_cycle_id': cycle.id,
              'crop_name': cycle.cropName,
              ...risk,
            });
          }
        }
      } catch (error, stackTrace) {
        debugPrint('Weather risk failed for crop cycle ${cycle.id}: $error');
        debugPrintStack(stackTrace: stackTrace);
        errors.add('${cycle.cropName} (cycle ${cycle.id}): $error');
      }
    }

    // Do not turn an API failure into a misleading "no alerts" state.
    // If at least one crop loaded successfully, keep its alerts visible.
    if (results.isEmpty && errors.isNotEmpty) {
      throw ApiException(
        'Could not load weather-risk data. ${errors.join(" | ")}',
      );
    }

    return results;
  }

  String _dateString(DateTime value) =>
      '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

  void _reload() {
    setState(() {
      _tasks = widget.auth.loadTasks(_targetDate);
      _weatherRisks = _loadWeatherRisks(_targetDate);
    });
  }

  Future<void> _chooseDate() async {
    final value = await showDatePicker(
      context: context,
      initialDate: _targetDate,
      firstDate: DateTime(2000),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (value == null || !mounted) return;

    setState(() {
      _targetDate = value;
      _weatherRisks = _loadWeatherRisks(value);
      _result = null;
      _error = null;
      _generating = true;
    });

    try {
      final result = await widget.auth.generateTasks(value);
      final tasks = await widget.auth.loadTasks(value);

      if (!mounted) return;

      setState(() {
        _tasks = Future.value(tasks);
        _result =
            '${result['tasks_created'] ?? 0} new task(s) created for '
            '${_dateString(value)}.';
      });
    } catch (error) {
      if (!mounted) return;

      setState(() {
        _tasks = widget.auth.loadTasks(value);
        _error = error is ApiException
            ? error.message
            : 'Could not generate tasks for this date.';
      });
    } finally {
      if (mounted) {
        setState(() => _generating = false);
      }
    }
  }

  Future<void> _generate() async {
    setState(() {
      _generating = true;
      _error = null;
      _result = null;
    });
    try {
      final result = await widget.auth.generateTasks(_targetDate);
      if (!mounted) return;
      final created = result['tasks_created'] ?? 0;
      setState(() {
        _result = '$created new task(s) created. ${result['message'] ?? ''}'
            .trim();
        _tasks = widget.auth.loadTasks(_targetDate);
        _weatherRisks = _loadWeatherRisks(_targetDate);
      });
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = error is ApiException
              ? error.message
              : 'Could not generate tasks. Check the backend and try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _generating = false);
    }
  }

  Future<void> _toggleTask(DailyTask task) async {
    if (_toggling.contains(task.id)) return;
    setState(() => _toggling.add(task.id));
    try {
      final done = task.status.toLowerCase() == 'completed';
      if (done) {
        await widget.auth.reopenTask(task.id);
      } else {
        await widget.auth.completeTask(task.id);
      }
      if (mounted) _reload();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              e is ApiException ? e.message : 'Could not update task.',
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _toggling.remove(task.id));
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(AppSpace.xxl),
    children: [
      Text('Daily Tasks', style: AppText.h1),
      const SizedBox(height: AppSpace.xs),
      Text(
        'Tasks are generated from verified active advisory rules for your crop cycles.',
        style: AppText.bodyMuted,
      ),
      const SizedBox(height: AppSpace.xl),

      // ── Controls ────────────────────────────────────────────
      Wrap(
        spacing: AppSpace.md,
        runSpacing: AppSpace.md,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          OutlinedButton.icon(
            onPressed: _chooseDate,
            icon: const Icon(Icons.calendar_today_outlined),
            label: Text(_dateString(_targetDate)),
          ),
          FilledButton.icon(
            onPressed: _generating ? null : _generate,
            icon: _generating
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.bolt_outlined),
            label: const Text('Generate Tasks'),
          ),
          IconButton(
            tooltip: 'Refresh tasks',
            onPressed: _reload,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),

      if (_error != null) ...[
        const SizedBox(height: AppSpace.lg),
        _Banner(message: _error!, isError: true),
      ],
      if (_result != null) ...[
        const SizedBox(height: AppSpace.lg),
        _Banner(message: _result!),
      ],

      const SizedBox(height: AppSpace.lg),
      Text('Weather Risk Alerts', style: AppText.h1),
      const SizedBox(height: AppSpace.sm),
      FutureBuilder<List<Map<String, dynamic>>>(
        future: _weatherRisks,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Padding(
              padding: EdgeInsets.all(AppSpace.md),
              child: Center(child: CircularProgressIndicator()),
            );
          }

          if (snapshot.hasError) {
            final error = snapshot.error;
            return _Banner(
              message: error is ApiException
                  ? error.message
                  : 'Could not load weather-risk alerts. Check the backend connection.',
              isError: true,
            );
          }

          final risks = snapshot.data ?? const [];

          if (risks.isEmpty) {
            return const _Banner(
              message:
                  'No matching weather-risk alerts were returned for this date. '
                  'This does not guarantee that the crop is risk-free.',
            );
          }

          return Column(
            children: risks.map((risk) {
              final name = _riskField(risk, [
                'risk',
                'disease_or_risk',
                'disease_name',
              ]);
              final marathiName = _riskField(risk, [
                'disease_name_marathi',
                'marathi_name',
                'Disease Name (Marathi)',
              ]);
              final crop = _riskField(risk, [
                'crop_name',
                'crop_scope_as_supplied',
                'crop',
              ]);
              final symptoms = _riskField(risk, [
                'symptoms_to_check',
                'symptoms_or_field_checks',
              ]);
              final prevention = _riskField(risk, [
                'prevention',
                'prevention_or_nonchemical_actions_as_supplied',
              ]);
              final profile = _riskField(risk, [
                'weather_profile',
                'weather_profile_as_supplied',
              ]);
              final weatherTrigger = _riskField(risk, [
                'weather_trigger_as_supplied',
                'weather_match_explanation',
              ]);
              final pathogen = _riskField(risk, [
                'pathogen_or_vector',
                'causal_organism',
              ]);
              final cycleId = risk['crop_cycle_id'];

              if (cycleId is! int) {
                return const SizedBox.shrink();
              }

              final riskName = name.isEmpty ? 'Potential crop risk' : name;
              final key = '$cycleId|${_dateString(_targetDate)}|$riskName';
              final questions = _questionsForRisk(riskName);
              final answers = _riskAnswers.putIfAbsent(key, () => {});
              final allAnswered = questions.every(
                (question) => answers.containsKey(question),
              );
              final anyYes = answers.values.any((answer) => answer);
              final guidance = allAnswered
                  ? _guidanceForAnswers(answers, prevention)
                  : '';

              return Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: AppSpace.md),
                padding: const EdgeInsets.all(AppSpace.lg),
                decoration: BoxDecoration(
                  color: AppColors.warning.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(AppSpace.radiusCard),
                  border: Border.all(
                    color: AppColors.warning.withValues(alpha: 0.5),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(
                          Icons.warning_amber_rounded,
                          color: AppColors.warning,
                        ),
                        const SizedBox(width: AppSpace.sm),
                        Expanded(child: Text(riskName, style: AppText.label)),
                      ],
                    ),
                    const SizedBox(height: AppSpace.xs),
                    Text('Crop: $crop', style: AppText.bodyMuted),
                    if (profile.isNotEmpty) ...[
                      const SizedBox(height: AppSpace.sm),
                      Text('Weather pattern: $profile'),
                    ],
                    if (marathiName.isNotEmpty)
                      _riskInfo('रोगाचे नाव (Marathi)', marathiName),
                    if (pathogen.isNotEmpty)
                      _riskInfo('Causal organism / vector', pathogen),
                    if (symptoms.isNotEmpty)
                      _riskInfo('Symptoms to inspect', symptoms),
                    if (prevention.isNotEmpty)
                      _riskInfo(
                        'Prevention and non-chemical actions',
                        prevention,
                      ),
                    const Divider(),
                    const SizedBox(height: AppSpace.sm),
                    Text(
                      'This is a potential weather risk, not a confirmed diagnosis. '
                      'Symptoms should be checked before viewing treatment information.',
                      style: AppText.small.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: AppSpace.md),
                    Text('Check your crop', style: AppText.label),
                    const SizedBox(height: AppSpace.sm),
                    ...questions.map((question) {
                      final selected = answers[question];

                      return Padding(
                        padding: const EdgeInsets.only(bottom: AppSpace.sm),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(question),
                            const SizedBox(height: 4),
                            Wrap(
                              spacing: 8,
                              children: [
                                ChoiceChip(
                                  label: const Text('Yes'),
                                  selected: selected == true,
                                  onSelected: (value) {
                                    setState(() {
                                      if (value) {
                                        answers[question] = true;
                                        _savedAssessments.remove(key);
                                      }
                                    });
                                  },
                                ),
                                ChoiceChip(
                                  label: const Text('No'),
                                  selected: selected == false,
                                  onSelected: (value) {
                                    setState(() {
                                      if (value) {
                                        answers[question] = false;
                                        _savedAssessments.remove(key);
                                      }
                                    });
                                  },
                                ),
                              ],
                            ),
                          ],
                        ),
                      );
                    }),
                    if (anyYes) ...[
                      const SizedBox(height: AppSpace.md),
                      OutlinedButton.icon(
                        icon: const Icon(Icons.medication_outlined),
                        label: const Text('View Treatment Information'),
                        onPressed: () => _showDiseaseTreatment(
                          crop: crop,
                          disease: riskName,
                        ),
                      ),
                    ],
                    if (allAnswered) ...[
                      const Divider(),
                      Text(
                        anyYes
                            ? 'Further inspection recommended'
                            : 'Monitoring guidance',
                        style: AppText.label,
                      ),
                      const SizedBox(height: AppSpace.xs),
                      Text(guidance),
                      const SizedBox(height: AppSpace.sm),
                      if (anyYes && prevention.isNotEmpty)
                        Text('Knowledge-base prevention guidance: $prevention'),
                      Text(
                        'Weather and symptom matches do not confirm a disease. '
                        'No automatic pesticide recommendation is made.',
                        style: AppText.small.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                      const SizedBox(height: AppSpace.md),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed:
                              _savingAssessments.contains(key) ||
                                  _savedAssessments.contains(key)
                              ? null
                              : () => _saveRiskAssessment(
                                  key: key,
                                  cropCycleId: cycleId,
                                  crop: crop,
                                  riskName: riskName,
                                  answers: Map<String, bool>.from(answers),
                                  guidance: guidance,
                                  details: [
                                    'Disease (English): $riskName',
                                    'Disease (Marathi): $marathiName',
                                    'Crop: $crop',
                                    'Weather profile: $profile',
                                    'Weather trigger: $weatherTrigger',
                                    'Causal organism/vector: $pathogen',
                                    'Symptoms: $symptoms',
                                    'Prevention: $prevention',
                                  ].join('\n'),
                                ),
                          icon: _savingAssessments.contains(key)
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.save_outlined),
                          label: Text(
                            _savedAssessments.contains(key)
                                ? 'Assessment Saved'
                                : _savingAssessments.contains(key)
                                ? 'Saving...'
                                : 'Save Assessment',
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              );
            }).toList(),
          );
        },
      ),

      const SizedBox(height: AppSpace.xl),

      // ── Task list ───────────────────────────────────────────
      FutureBuilder<List<DailyTask>>(
        future: _tasks,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(AppSpace.xl),
                child: CircularProgressIndicator(),
              ),
            );
          }
          if (snapshot.hasError) {
            final error = snapshot.error;
            return _Banner(
              message: error is ApiException
                  ? error.message
                  : 'Could not load tasks.',
              isError: true,
            );
          }
          final rows = snapshot.data ?? const <DailyTask>[];
          if (rows.isEmpty) {
            return _Banner(
              message:
                  'No tasks for ${_dateString(_targetDate)}. '
                  'Press "Generate Tasks" to create tasks for this date.',
            );
          }

          // Group by status
          final pending = rows
              .where((t) => t.status.toLowerCase() != 'completed')
              .toList();
          final done = rows
              .where((t) => t.status.toLowerCase() == 'completed')
              .toList();

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (pending.isNotEmpty) ...[
                _SectionHeader(
                  label: 'To Do',
                  count: pending.length,
                  color: AppColors.primary,
                ),
                ...pending.map(
                  (t) => _TaskCard(
                    task: t,
                    toggling: _toggling.contains(t.id),
                    onToggle: () => _toggleTask(t),
                  ),
                ),
              ],
              if (done.isNotEmpty) ...[
                const SizedBox(height: AppSpace.md),
                _SectionHeader(
                  label: 'Completed',
                  count: done.length,
                  color: AppColors.textSecondary,
                ),
                ...done.map(
                  (t) => _TaskCard(
                    task: t,
                    toggling: _toggling.contains(t.id),
                    onToggle: () => _toggleTask(t),
                  ),
                ),
              ],
            ],
          );
        },
      ),
    ],
  );
}

// ──────────────────────────────────────────────────────────────────
// Sub-widgets
// ──────────────────────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  final String label;
  final int count;
  final Color color;

  const _SectionHeader({
    required this.label,
    required this.count,
    required this.color,
  });

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpace.sm),
    child: Row(
      children: [
        Text(label, style: AppText.label.copyWith(color: color)),
        const SizedBox(width: AppSpace.sm),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            '$count',
            style: AppText.small.copyWith(
              color: color,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ],
    ),
  );
}

class _TaskCard extends StatelessWidget {
  final DailyTask task;
  final bool toggling;
  final VoidCallback onToggle;

  const _TaskCard({
    required this.task,
    required this.toggling,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final done = task.status.toLowerCase() == 'completed';

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: AppSpace.md),
      padding: const EdgeInsets.all(AppSpace.lg),
      decoration: BoxDecoration(
        color: done ? AppColors.primaryLight : AppColors.surface,
        borderRadius: BorderRadius.circular(AppSpace.radiusCard),
        border: Border.all(color: done ? AppColors.accent : AppColors.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Toggle button
          GestureDetector(
            onTap: toggling ? null : onToggle,
            child: toggling
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Icon(
                    done ? Icons.check_circle : Icons.circle_outlined,
                    color: done ? AppColors.primary : AppColors.textSecondary,
                    size: 22,
                  ),
          ),
          const SizedBox(width: AppSpace.md),

          // Content
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  task.title,
                  style: AppText.label.copyWith(
                    decoration: done ? TextDecoration.lineThrough : null,
                    color: done ? AppColors.textSecondary : null,
                  ),
                ),
                if (task.description?.isNotEmpty == true) ...[
                  const SizedBox(height: AppSpace.xs),
                  _TaskDescription(description: task.description!),
                ],
                const SizedBox(height: AppSpace.sm),
                Row(
                  children: [
                    _TypeChip(type: task.sourceRuleType),
                    const Spacer(),
                    // Tap label hint
                    Text(
                      done ? 'Tap to reopen' : 'Tap ✓ to complete',
                      style: AppText.small.copyWith(
                        color: AppColors.textSecondary,
                        fontSize: 10,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TaskDescription extends StatelessWidget {
  final String description;

  const _TaskDescription({required this.description});

  @override
  Widget build(BuildContext context) {
    const marker = 'DRENCH_DAY_1_30 source details';
    final markerIndex = description.indexOf(marker);

    if (markerIndex < 0) {
      return Text(description, style: AppText.bodyMuted);
    }

    final monitoringText = description.substring(0, markerIndex).trim();
    final drenchText = description.substring(markerIndex).trim();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (monitoringText.isNotEmpty) ...[
          Text(monitoringText, style: AppText.bodyMuted),
          const SizedBox(height: AppSpace.md),
        ],
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(AppSpace.md),
          decoration: BoxDecoration(
            color: AppColors.warning.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(AppSpace.radiusCard),
            border: Border.all(
              color: AppColors.warning.withValues(alpha: 0.45),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Drench schedule — reference only', style: AppText.label),
              const SizedBox(height: AppSpace.xs),
              Text(
                'These source details are not an approved application '
                'instruction. Verify the recommendations and product '
                'labels with a qualified agricultural adviser.',
                style: AppText.small.copyWith(color: AppColors.textSecondary),
              ),
              const SizedBox(height: AppSpace.sm),
              const Divider(),
              SelectableText(drenchText, style: AppText.bodyMuted),
            ],
          ),
        ),
      ],
    );
  }
}

class _TypeChip extends StatelessWidget {
  final String? type;

  const _TypeChip({this.type});

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (type) {
      'fertilizer_stage' => ('Fertilizer', AppColors.warning),
      'fertilizer_onetime' => ('One-time Fertilizer', AppColors.attention),
      'irrigation' ||
      'irrigation_check' => ('Irrigation', const Color(0xFF1565C0)),
      'stage_milestone' => ('Growth Stage', AppColors.primary),
      _ => ('Task', AppColors.textSecondary),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: AppText.small.copyWith(
          color: color,
          fontWeight: FontWeight.w600,
          fontSize: 10,
        ),
      ),
    );
  }
}

class _Banner extends StatelessWidget {
  final String message;
  final bool isError;

  const _Banner({required this.message, this.isError = false});

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(AppSpace.lg),
    decoration: BoxDecoration(
      color: (isError ? AppColors.danger : AppColors.primary).withValues(
        alpha: 0.08,
      ),
      borderRadius: BorderRadius.circular(AppSpace.radiusCard),
    ),
    child: Text(
      message,
      style: AppText.body.copyWith(
        color: isError ? AppColors.danger : AppColors.textPrimary,
      ),
    ),
  );
}
