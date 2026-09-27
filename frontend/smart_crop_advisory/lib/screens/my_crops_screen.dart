import 'package:flutter/material.dart';
import '../data/mock/mock_data.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';
import '../widgets/crop_card.dart';

class MyCropsScreen extends StatelessWidget {
  const MyCropsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final crops = MockData.crops;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpace.xxl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ---------- Header ----------
          Row(children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('My Crops', style: AppText.h1),
                  const SizedBox(height: 6),
                  Text('${crops.length} crops across your farms',
                      style: AppText.bodyMuted),
                ],
              ),
            ),
            FilledButton.icon(
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Add Crop — coming soon')),
                );
              },
              icon: const Icon(Icons.add, size: 18),
              label: const Text('Add Crop'),
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(
                    horizontal: 20, vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppSpace.radiusBtn),
                ),
              ),
            ),
          ]),
          const SizedBox(height: AppSpace.xxl),

          // ---------- Grid ----------
          LayoutBuilder(builder: (context, c) {
            int cols;
            if (c.maxWidth >= 1100) {
              cols = 3;
            } else if (c.maxWidth >= 700) {
              cols = 2;
            } else {
              cols = 1;
            }

            return GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: crops.length,
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: cols,
                crossAxisSpacing: AppSpace.lg,
                mainAxisSpacing: AppSpace.lg,
                childAspectRatio: 0.72,
              ),
              itemBuilder: (_, i) {
                final crop = crops[i];
                return CropCard(
                  crop: crop,
                  onTap: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('${crop.name} details — coming soon')),
                    );
                  },
                );
              },
            );
          }),
        ],
      ),
    );
  }
}