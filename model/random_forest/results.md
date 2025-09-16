DESKTOP-6HFGBTP\OneDrive\Desktop\Music-Therapy-Box\model\random_forest> python synthesize_hr_eda_dataset.py
100%|██████████████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:03<00:00, 329.66it/s]
Generated dataset shape: (1000, 19)
label                     0           1
hr_mean   count  518.000000  482.000000
          mean    68.271290   76.113978
          std      5.871021    7.540861
          min     52.570440   56.082128
          25%     63.842646   71.346896
          50%     68.476957   75.853695
          75%     72.188104   80.795892
          max     90.175975   97.134718
eda_mean  count  518.000000  482.000000
          mean     3.006726    3.006024
          std      1.191223    1.206703
          min      0.493553    0.496336
          25%      2.125613    2.248686
          50%      2.982653    2.995642
          75%      3.912420    3.831919
          max      6.376358    7.415273
scr_count count  518.000000  482.000000
          mean     0.472973    2.356846
          std      0.718802    1.526360
          min      0.000000    0.000000
          25%      0.000000    1.000000
          50%      0.000000    2.000000
          75%      1.000000    3.000000
          max      4.000000   11.000000
Saved synthetic_hr_eda_windows.csv
PS C:\Users\collins.DESKTOP-6HFGBTP\OneDrive\Desktop\Music-Therapy-Box\model\random_forest>

Saved synthetic_hr_eda_windows.csv
PS C:\Users\collins.DESKTOP-6HFGBTP\OneDrive\Desktop\Music-Therapy-Box\model\random_forest> python random_forest_train.py
Accuracy: 0.945
              precision    recall  f1-score   support

           0       0.92      0.98      0.95       105
           1       0.98      0.91      0.94        95

    accuracy                           0.94       200
   macro avg       0.95      0.94      0.94       200
weighted avg       0.95      0.94      0.94       200

 Model saved as stress_random_forest.pkl
PS C:\Users\collins.DESKTOP-6HFGBTP\OneDrive\Desktop\Music-Therapy-Box\model\random_forest>