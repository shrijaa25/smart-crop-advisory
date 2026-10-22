import 'package:flutter/material.dart';

import '../models/crop_cycle.dart';
import '../models/daily_task.dart';
import '../models/farm.dart';
import '../services/api_client.dart';
import '../services/auth_controller.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';

class HomeScreen extends StatefulWidget {
  final AuthController auth;

  const HomeScreen({super.key, required this.auth});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<_HomeData> _data;

  @override
  void initState() {
    super.initState();
    _data = _loadAll();
  }

  /// Auto-generates today's tasks first, then loads farms, crops & tasks.
  Future<_HomeData> _loadAll() async {
    // Silently generate tasks for today (safe to call repeatedly — no duplicates)
    try {
      await widget.auth.generateTasks(DateTime.now());
    } catch (_) {
      // Don't block the UI if generation fails
    }

    final results = await Future.wait([
      widget.auth.loadFarms(),
      widget.auth.loadCropCycles(),
      widget.auth.loadTasksForToday(),
    ]);

    return _HomeData(
      farms: results[0] as List<Farm>,
      cycles: results[1] as List<CropCycle>,
      tasks: results[2] as List<DailyTask>,
    );
  }

  void _reload() => setState(() => _data = _loadAll());

  @override
  Widget build(BuildContext context) {
    final name =
        widget.auth.profile?.fullName.trim().split(RegExp(r'\s+')).first ??
        'Farmer';

    return RefreshIndicator(
      onRefresh: () async => _reload(),
      child: FutureBuilder<_HomeData>(
        future: _data,
        builder: (context, snapshot) {
          final loading = snapshot.connectionState == ConnectionState.waiting;
          final data = snapshot.data;
          final error = snapshot.error;

          return ListView(
            padding: const EdgeInsets.all(AppSpace.xxl),
            children: [
              // ── Header ──────────────────────────────────────────
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Welcome back, $name 👋', style: AppText.h1),
                        const SizedBox(height: AppSpace.xs),
                        Text(
                          _todayString(),
                          style: AppText.bodyMuted,
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: 'Refresh',
                    onPressed: _reload,
                    icon: loading
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.refresh),
                  ),
                ],
              ),
              const SizedBox(height: AppSpace.xxl),

              // ── Error banner ────────────────────────────────────
              if (error != null) ...[
                _notice(
                  icon: Icons.error_outline,
                  color: AppColors.danger,
                  message: error is ApiException
                      ? error.message
                      : 'Could not load your dashboard. Pull down to retry.',
                ),
                const SizedBox(height: AppSpace.xl),
              ],

              // ── Active crops ────────────────────────────────────
              Text("Your active crops", style: AppText.h2),
              const SizedBox(height: AppSpace.md),

              if (loading)
                const _Shimmer()
              else if (data == null || data.cycles.isEmpty)
                _notice(
                  icon: Icons.eco_outlined,
                  color: AppColors.primary,
                  message:
                      'No active crops yet. Go to "Farm & Crops" to register your first crop.',
                )
              else
                ...data.cycles
                    .where((c) => c.status == 'active')
                    .map((c) => _CropCard(
                          auth: widget.auth,
                          cycle: c,
                          farmName: data.farms
                              .where((f) => f.id == c.farmId)
                              .map((f) => f.name)
                              .firstOrNull,
                        )),

              const SizedBox(height: AppSpace.xxl),

              // ── Today's tasks ────────────────────────────────────
              Row(
                children: [
                  Expanded(child: Text("Today's tasks", style: AppText.h2)),
                  if (!loading)
                    Text(
                      data?.tasks.isEmpty == true
                          ? 'None'
                          : '${data?.tasks.length ?? 0} task(s)',
                      style: AppText.small,
                    ),
                ],
              ),
              const SizedBox(height: AppSpace.md),

              if (loading)
                const _Shimmer()
              else if (data == null || data.tasks.isEmpty)
                _notice(
                  icon: Icons.event_available_outlined,
                  color: AppColors.primary,
                  message:
                      'No tasks for today. Tasks are generated from verified crop advisory rules.',
                )
              else
                ...data.tasks.map(
                  (task) => _TaskTile(
                    task: task,
                    onToggle: (id, isDone) async {
                      try {
                        if (isDone) {
                          await widget.auth.completeTask(id);
                        } else {
                          await widget.auth.reopenTask(id);
                        }
                        _reload();
                      } catch (_) {}
                    },
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  String _todayString() {
    final now = DateTime.now();
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December',
    ];
    return '${months[now.month - 1]} ${now.day}, ${now.year}';
  }

  Widget _notice({
    required IconData icon,
    required Color color,
    required String message,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppSpace.lg),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppSpace.radiusCard),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: AppSpace.md),
          Expanded(child: Text(message, style: AppText.body)),
        ],
      ),
    );
  }
}

// ──────────────────────────────────────────────────────────────────
// Data holder
// ──────────────────────────────────────────────────────────────────

class _HomeData {
  final List<Farm> farms;
  final List<CropCycle> cycles;
  final List<DailyTask> tasks;

  const _HomeData({
    required this.farms,
    required this.cycles,
    required this.tasks,
  });
}

// ──────────────────────────────────────────────────────────────────
// Crop card with live stage lookup
// ──────────────────────────────────────────────────────────────────

class _CropCard extends StatefulWidget {
  final AuthController auth;
  final CropCycle cycle;
  final String? farmName;

  const _CropCard({
    required this.auth,
    required this.cycle,
    required this.farmName,
  });

  @override
  State<_CropCard> createState() => _CropCardState();
}

class _CropCardState extends State<_CropCard> {
  late Future<Map<String, dynamic>> _stage;

  @override
  void initState() {
    super.initState();
    _stage = widget.auth.loadCropStage(widget.cycle.id, DateTime.now());
  }

  @override
  Widget build(BuildContext context) {
    final crop = widget.cycle;
    final cropLabel = crop.cropName == 'chilli' ? '🌶 Chilli' : '🍅 Tomato';

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: AppSpace.md),
      padding: const EdgeInsets.all(AppSpace.lg),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppSpace.radiusCard),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '$cropLabel${crop.variety?.isNotEmpty == true ? ' · ${crop.variety}' : ''}',
                  style: AppText.label,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 3,
                ),
                decoration: BoxDecoration(
                  color: AppColors.primaryLight,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  crop.status.toUpperCase(),
                  style: AppText.small.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w700,
                    fontSize: 10,
                  ),
                ),
              ),
            ],
          ),
          if (widget.farmName != null) ...[
            const SizedBox(height: AppSpace.xs),
            Text(widget.farmName!, style: AppText.small),
          ],
          const SizedBox(height: AppSpace.sm),
          FutureBuilder<Map<String, dynamic>>(
            future: _stage,
            builder: (context, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return Text('Loading crop stage…', style: AppText.bodyMuted);
              }
              if (snap.hasError) {
                return Text('Stage unavailable', style: AppText.bodyMuted);
              }
              final s = snap.data ?? {};
              final age = s['crop_age_days'] as int?;
              final stageName = s['stage_name'] as String?;

              if (age != null && age < 0) {
                return Text('Not yet transplanted', style: AppText.bodyMuted);
              }

              return Row(
                children: [
                  if (age != null) ...[
                    _Chip(label: 'Day $age', color: AppColors.primary),
                    const SizedBox(width: AppSpace.sm),
                  ],
                  if (stageName != null)
                    _Chip(label: stageName, color: AppColors.accent),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  final String label;
  final Color color;

  const _Chip({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: AppText.small.copyWith(
          color: color,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

// ──────────────────────────────────────────────────────────────────
// Task tile with tap-to-toggle done
// ──────────────────────────────────────────────────────────────────

class _TaskTile extends StatelessWidget {
  final DailyTask task;
  final void Function(int id, bool markDone) onToggle;

  const _TaskTile({required this.task, required this.onToggle});

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
        border: Border.all(
          color: done ? AppColors.accent : AppColors.border,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          GestureDetector(
            onTap: () => onToggle(task.id, !done),
            child: Icon(
              done ? Icons.check_circle : Icons.circle_outlined,
              color: done ? AppColors.primary : AppColors.textSecondary,
              size: 22,
            ),
          ),
          const SizedBox(width: AppSpace.md),
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
                  Text(task.description!, style: AppText.bodyMuted),
                ],
                const SizedBox(height: AppSpace.xs),
                _TypeBadge(type: task.sourceRuleType),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TypeBadge extends StatelessWidget {
  final String? type;

  const _TypeBadge({this.type});

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (type) {
      'fertilizer_stage' => ('Fertilizer', AppColors.warning),
      'fertilizer_onetime' => ('One-time Fertilizer', AppColors.attention),
      'irrigation' || 'irrigation_check' => ('Irrigation', const Color(0xFF1565C0)),
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

// ──────────────────────────────────────────────────────────────────
// Simple shimmer placeholder
// ──────────────────────────────────────────────────────────────────

class _Shimmer extends StatelessWidget {
  const _Shimmer();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: List.generate(
        2,
        (_) => Container(
          height: 72,
          margin: const EdgeInsets.only(bottom: AppSpace.md),
          decoration: BoxDecoration(
            color: AppColors.border,
            borderRadius: BorderRadius.circular(AppSpace.radiusCard),
          ),
        ),
      ),
    );
  }
}
